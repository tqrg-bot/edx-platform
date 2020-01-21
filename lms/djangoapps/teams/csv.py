"""
CSV processing and generation utilities for Teams LMS app.
"""



import logging
import csv
from lms.djangoapps.teams.models import CourseTeam, CourseTeamMembership
from student.models import CourseAccessRole, CourseEnrollment
from django.contrib.auth.models import User




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

    # the list of validation errors
    error_list = []
    teamset_names_list = []
    # this is a dictionary of dictionaries that ensures that a student can belong to
    # one and only one team in a teamset
    teamset_membership_dictionary = {}
    # the currently selected user
    user = ''

    def set_team_membership_from_csv(self, course, input_file):
        """
        Assigns team membership based on the content of an uploaded CSV file.
        Returns true if there were no issues.

        Arguments:
            course (CourseDescriptor): Course module for which team membership needs to be set.
        """
        error_list = []
        teamset_names_list = []
        teamset_membership_dictionary = {}
        course_key = course.id
        file_content = input_file.read().decode("utf-8")
        all_rows = file_content.split("\r\n")
        header_row = all_rows[0].split(",")
        validate_teamsets(header_row)
        import pdb; pdb.set_trace()
        # process student rows:
        for i in range(1,len(all_rows)):
            if row_data[0]: # avoid processing rows with empty user names (excel copy and paste)
                reset_user(row_data[0])
                row_data = all_rows[i].split(",")
                if validate_user_entry(row_data, course) == False:
                    return False
                add_user_to_team(row_data, course)
                import pdb;pdb.set_trace()

        return True

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
            teamset_names_list.append(header_row[i])
            teamset_membership_dictionary[header_row[i]]=[]
        return True

    def validate_user_entry(self, user_row, course):
        """
        Validates user row entry. Returns true if there are no errors.
        user_row is the list representation of an input row. It will have the following formta:
        use_id, enrollment_mode, <Team_Name_1>,...,<Team_Name_n>
        Team_Name_x are optional and can be a sparse list i.e:
        andrew,masters,team1,,team3
        joe,masters,,team2,team3
        """
        import pdb;pdb.set_trace()
        if not CourseEnrollment.is_enrolled(user_row[0], course.id):
            error_list.append('User {} is not enrolled in this course.', user_row[0])
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

        username = user_row[0]
        try:
            import pdb;pdb.set_trace()
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # TODO - handle user key case
            error_list.append('User with username ' + username + ' does not exist')
            #return Response(status=status.HTTP_404_NOT_FOUND)

        for i in range(2, len(user_row)):
            team_id = user_row[i]
            try:
                team = CourseTeam.objects.get(team_id=team_id)
            except CourseTeam.DoesNotExist:
                course_module = modulestore().get_course(course.id)
                team = CourseTeam.create(name=team_name,course_id=course.id,topic_id=topic_2_id)
                team.save()

            # if not has_team_api_access(request.user, team.course_id, access_username=username):
            #     return Response(status=status.HTTP_404_NOT_FOUND)

            #if not has_specific_team_access(request.user, team):
            #    return Response(status=status.HTTP_403_FORBIDDEN)

            course_module = modulestore().get_course(team.course_id)
            # This should use `calc_max_team_size` instead of `default_max_team_size` (TODO MST-32).
            max_team_size = course_module.teams_configuration.default_max_team_size
            if max_team_size is not None and team.users.count() >= max_team_size:
                error_list.append('Team ' + team_id + ' is already full.')
                break;

            # if not can_user_modify_team(request.user, team):
            #     return Response(
            #         build_api_error(ugettext_noop("You can't join an instructor managed team.")),
            #         status=status.HTTP_403_FORBIDDEN
            #     )

            try:
                membership = team.add_user(user)
                emit_team_event(
                    'edx.team.learner_added',
                    team.course_id,
                    {
                        'team_id': team.team_id,
                        'user_id': user.id,
                        'add_method': 'joined_from_team_view' if user == request.user else 'added_by_another_user'
                    }
                )
            except AlreadyOnTeamInCourse:
                error_list.append('The user ' + username + ' is already a member of a team in this course.')
                break
            except NotEnrolledInCourseForTeam:
                error_list.append('The user ' + username + 'is not enrolled in the course associated with this team.')
                break


    def reset_user(self, user_name):
        """
        Resets the class global user object variable from the provided username/email/user locator.
        If a matching user is not found, throws exception and stops processing.
        user_name: the user_name/email/user locator
        """
        user = ''
        try:
            import pdb;pdb.set_trace()
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # TODO - handle user key case
            error_list.append('User with username ' + username + ' does not exist')
            #return Response(status=status.HTTP_404_NOT_FOUND)

    def debug_get_hardcoded_team():
        return CourseTeam.objects.get(team_id='Team 1')


    def create_course_team(self, team_name, discussion_topic_id, course_id, topic_id):
        team = CourseTeam.create(
            name=team_name,
            course_id=validated_data.get("course_id"),
            # description=validated_data.get("description", ''),
            topic_id=validated_data.get("topic_id", ''),
            #country=validated_data.get("country", ''),
            # language=validated_data.get("language", ''),
            #organization_protected=validated_data.get("organization_protected", False)
        )
        team.save()

