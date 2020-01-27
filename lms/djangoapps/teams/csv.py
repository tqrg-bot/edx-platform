"""
CSV processing and generation utilities for Teams LMS app.
"""

import csv
from django.contrib.auth.models import User
from student.models import CourseEnrollment
from xmodule.modulestore.django import modulestore

from lms.djangoapps.teams.models import CourseTeam
from .errors import AlreadyOnTeamInCourse, NotEnrolledInCourseForTeam
from .utils import emit_team_event


def load_team_membership_csv(course, response):
    """
    Load a CSV detailing course membership.

    Arguments:
        course (CourseDescriptor): Course module for which CSV
            download has been requested.
        response (HttpResponse): Django response object to which
            the CSV content will be written.
    """
    # This function needs to be implemented (TODO MST-31).
    _ = course
    not_implemented_message = (
        "Team membership CSV download is not yet implemented."
    )
    response.write(not_implemented_message + "\n")


class TeamMemberShipImportManager(object):
    """
    A manager class that is responsible the import process of csv file including validation and creation of
    team_courseteam and teams_courseteammembership objects.
    """

    def __init__(self):
        # the list of validation errors
        self.error_list = []
        self.teamset_names_list = []
        # this is a dictionary of dictionaries that ensures that a student can belong to
        # one and only one team in a teamset
        self.teamset_membership_dictionary = {}
        # dictionary that matches column index to a teamset name. Used when creating teams to get the right teamset
        self.teamset_index_dictionary = {}
        # the currently selected user
        self.user = ''
        self.number_of_record_added = 0
        # stores the course module that will be used to get course metadata
        self.course_module = ''

    @property
    def import_succeeded(self):
        """
        Helper wrapper that tells us the status of the import
        """
        return len(self.error_list) == 0

    def set_team_membership_from_csv(self, course, input_file):
        """
        Assigns team membership based on the content of an uploaded CSV file.
        Returns true if there were no issues.

        Arguments:
            course (CourseDescriptor): Course module for which team membership needs to be set.
        """
        self.error_list = []
        self.teamset_names_list = []
        self.teamset_membership_dictionary = {}
        self.course_module = modulestore().get_course(course.id)
        all_rows = [row for row in csv.reader(input_file.read().decode('utf-8').splitlines())]
        header_row = all_rows[0]
        if self.validate_teamsets(header_row):
            # process student rows:
            for i in range(1, len(all_rows)):
                row_data = all_rows[i]
                if row_data[0]:  # avoid processing rows with empty user names (excel copy and paste)
                    self.reset_user(row_data[0])
                    if self.validate_user_entry(course) is False:
                        return False
                    self.add_user_to_team(row_data, course)

            return True
        return False

    def validate_teamsets(self, header_row):
        """
        Validates team set names. Returns true if there are no errors.
        Also populates teh teamset_names_list.
        header_row is the list representation of the header row of the input file. It will have
        the following format:
        user, mode, <teamset_1_name>,...,<teamset_n_name>
        where teamset_X_name must be a valid name of an existing teamset.
        """
        for i in range(2, len(header_row)):
            team_config = self.course_module.teams_configuration
            if not header_row[i] in [ts.teamset_id for ts in team_config.teamsets]:
                self.error_list.append("Teamset named " + header_row[i] + " does not exist.")
                return False
            self.teamset_names_list.append(header_row[i])
            self.teamset_membership_dictionary[header_row[i]] = []
            self.teamset_index_dictionary[i] = header_row[i]
        return True

    def validate_user_entry(self, course):
        """
        Validates user row entry. Returns true if there are no errors.
        user_row is the list representation of an input row. It will have the following formta:
        use_id, enrollment_mode, <Team_Name_1>,...,<Team_Name_n>
        Team_Name_x are optional and can be a sparse list i.e:
        andrew,masters,team1,,team3
        joe,masters,,team2,team3
        """
        if not CourseEnrollment.is_enrolled(self.user, course.id):
            self.error_list.append('User ' + self.user.username + ' is not enrolled in this course.')
            return False

        return True

    def add_user_to_team(self, user_row, course):
        """
        Creates a CourseTeamMembership entry - i.e: a relationship between a user and a team.
        user_row is the list representation of an input row. It will have the following formta:
        use_id, enrollment_mode, <Team_Name_1>,...,<Team_Name_n>
        Team_Name_x are optional and can be a sparse list i.e:
        andrew,masters,team1,,team3
        joe,masters,,team2,team3
        """
        for i in range(2, len(user_row)):
            team_name = user_row[i]
            if team_name:
                try:
                    # checks for a team inside a specific team set. This way team names can be duplicated across
                    # teamsets
                    team = CourseTeam.objects.get(name=team_name, topic_id=self.teamset_index_dictionary[i])
                except CourseTeam.DoesNotExist:
                    # course_module = modulestore().get_course(course.id)
                    team = CourseTeam.create(name=team_name, course_id=course.id, description='Import from csv',
                                             topic_id=self.teamset_index_dictionary[i]
                                             )
                    team.save()

                # if not has_team_api_access(request.user, team.course_id, access_username=username):
                #     return Response(status=status.HTTP_404_NOT_FOUND)

                # if not has_specific_team_access(request.user, team):
                #    return Response(status=status.HTTP_403_FORBIDDEN)

                # course_module = modulestore().get_course(course.id)
                # This should use `calc_max_team_size` instead of `default_max_team_size` (TODO MST-32).
                max_team_size = self.course_module.teams_configuration.default_max_team_size
                if max_team_size is not None and team.users.count() >= max_team_size:
                    self.error_list.append('Team ' + team.team_id + ' is already full.')
                    break
                try:
                    emit_team_event(
                        'edx.team.learner_added',
                        team.course_id,
                        {
                            'team_id': team.team_id,
                            'user_id': self.user.id,
                            'add_method': 'added_by_another_user'
                        }
                    )
                    self.number_of_record_added += 1
                except AlreadyOnTeamInCourse:
                    self.error_list.append(
                        'The user ' + self.user.username + ' is already a member of a team in this course.')
                    break
                except NotEnrolledInCourseForTeam:
                    self.error_list.append(
                        'The user ' + self.user.username + 'is not enrolled in the course associated with this team.')
                    break

    def reset_user(self, user_name):
        """
        Resets the class user object variable from the provided username/email/user locator.
        If a matching user is not found, throws exception and stops processing.
        user_name: the user_name/email/user locator
        """
        try:
            self.user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            self.user = User.objects.get(email=user_name)
        except User.DoesNotExist:
            # TODO - handle user key case
            self.error_list.append('User with username ' + user_name + ' does not exist')
