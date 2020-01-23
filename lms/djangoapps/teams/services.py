""" Services to expose the Teams API to XBlocks """


from django.urls import reverse


class TeamsService(object):
    """ Functions to provide teams functionality to XBlocks"""
    def get_team(self, user, course_id, topic_id):
        from . import api
        return api.get_team_for_user_course_topic(user, course_id, topic_id)

    def get_team_detail_url(self, team):
        """ Returns the url to the detail view for the given team """
        teams_dashboard_url = reverse('teams_dashboard', kwargs={'course_id': team.course_id})
        # Unfortunately required since this URL resolution is done in a Backbone view
        return "{teams_dashboard_url}#teams/{topic_id}/{team_id}".format(
            teams_dashboard_url=teams_dashboard_url,
            topic_id=team.topic_id,
            team_id=team.team_id,
        )

    def get_team_anonymous_user_ids(self, user, team):
        from . import api
        return api.get_team_anonymous_user_ids(user, team)
