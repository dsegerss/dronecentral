import os
import abc
import cgi
import webapp2
import jinja2
from google.appengine.api import urlfetch
from google.appengine.ext import db

DEFAULT_SURVEY_NAME = "ACTIVESURVEY"

GCM_SERVER = "https://android.googleapis.com/gcm/send"
GOOGLE_API_KEY = "AIzaSyBes8BF3izsF6xmMAkqFl5LOFKXOcYcswU"
REGISTRATION_ID = "Registration Id of the target device"

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def survey_key(survey_name=DEFAULT_SURVEY_NAME):
    """
    Constructs a Datastore key for a Survey entity
    with survey_name.
    """
    return db.Key(survey_name)


class StatusReport(db.Model):
    """Models a drone status report"""
    active = db.BooleanProperty(indexed=False)
    autopilot = db.BooleanProperty(indexed=False)
    current_waypoint = db.IntegerProperty(indexed=False)
    speed = db.FloatProperty(indexed=False)
    heading = db.FloatProperty(indexed=False)
    turn_rate = db.FloatProperty(indexed=False)
    battery_status = db.IntegerProperty(indexed=False)
    lon = db.FloatProperty(indexed=False)
    lat = db.FloatProperty(indexed=False)
    reportTime = db.DateTimeProperty(auto_now_add=True)


class WaypointList(db.Model):
    """Models a list of waypoints"""
    waypoints = db.ListProperty(db.GeoPt)


class BaseMessage(webapp2.RequestHandler):
    """
    Class containing basic functionality to communicate
    with drone using GCM
    """

    def makeRequest(self):
        """Create request to GCM"""
        request = "registration_ids=%i&command=%s&value=%s" % (
            REGISTRATION_ID,
            self.getCommand(),
            self.getValue())
        return request

    def makeNotification(self, msg, result):
        """ Show notification of sent message and received feedback"""
        self.response.headers['Content-Type'] = 'text/html'
        self.response.set_status(200, "OK" )
        self.response.out.write('<html>')
        self.response.out.write('<head>')
        self.response.out.write('<title>')
        self.response.out.write('Notifiation')
        self.response.out.write('</title>')
        self.response.out.write('</head>')
        self.response.out.write('<body>')
        self.response.out.write('Sent message: %s' % msg)
        self.response.out.write('Server response, status: %s' % result.content)
        self.response.out.write('</body>')
        self.response.out.write('</html>')

    @abc.abstractmethod
    def getValue(self):
        """Abstract method to acquire value for message"""

    @abc.abstractmethod
    def getCommand(self):
        """Abstract method to acquire command for message"""

    def post(self):
        """ Send message using GCM and wait for feedback"""

        request = self.makeRequest()

        result = urlfetch.fetch(
            url="GCM_SERVER",
            payload=request,
            method=urlfetch.POST,
            headers={'Content-Type':
                         'application/x-www-form-urlencoded;charset=UTF-8',
                     'Authorization': 'key=' + GOOGLE_API_KEY}
            )

        self.makeNotification(result)


class GetStatus(BaseMessage):

    def getCommand(self):
        return "GETSTATUS"

    def getValue(self):
        return ""


class AddWaypoint(BaseMessage):

    def getCommand(self):
        return "SETWP"    

    def getValue(self):
        lat = cgi.escape(self.request.get('wp_lat'))
        lon = cgi.escape(self.request.get('wp_lon'))
        return "%s,%s" % (lon, lat)


class DeleteWaypoints(webapp2.RequestHandler):
    """Delete all waypoint lists from datastore"""

    def post():
        wp_list = WaypointList.get(DEFAULT_SURVEY_NAME)
        wp_list.delete()


class DeleteReports(webapp2.RequestHandler):
    """Delete all reports from datastore"""

    def post():
        query = StatusReport.all()
        reports = query.fetch(200)

        for report in reports:
            report.delete()


class PlotWaypoints(webapp2.RequestHandler):
    """Plot waypoints on map"""


class PlotReports(webapp2.RequestHandler):
    """Plot reports on map"""


class UploadWaypoints():
    """Upload waypoint list to datastore"""

    def post(self):
        survey_name = self.request.get('survey_name',
                                       DEFAULT_SURVEY_NAME)
        waypoint_list = WaypointList(parent=survey_key(survey_name))
        waypoint_string = self.request.POST.get('waypoint-file').file.read()
        waypoints = (map(float, wp.split(',')) for
                     wp in waypoint_string.split(";"))
        waypoint_list.waypoints = [db.GeoPt(wp[1], wp[0]) for wp in waypoints]
        waypoint_list.put()


class SetStatus(webapp2.RequestHandler):
    """Upload status report to datastore"""

    def post(self):
        survey_name = self.request.get('survey_name',
                                       DEFAULT_SURVEY_NAME)
        report = StatusReport(parent=survey_key(survey_name))
        report.autopilot = self.request.get('autopilot').lower() == 'true'
        report.active = self.request.get('active').lower() == 'true'
        report.current_waypoint = int(float(self.request.get('cwp')))
        report.speed = float(self.request.get('speed'))
        report.heading = float(self.request.get('heading'))
        report.turn_rate = float(self.request.get('turn_rate'))
        report.battery_status = int(float(self.request.get('battery_status')))
        report.put()
        #query_params = {'survey_name': survey_name}
        #self.redirect('/?' + urllib.urlencode(query_params))


def getWaypoints():
    """Get waypoints from datastore and return as javascript"""
    try:
        wp_list = db.get(DEFAULT_SURVEY_NAME)
    except:
        return [db.GeoPt(58.2, 15.1),
                db.GeoPt(58.22, 15.101)]

    return wp_list


class MainPage(webapp2.RequestHandler):

    def get(self):
        """Write main page"""
        report_query = StatusReport.all()
        reports = report_query.fetch(10)

        for report in reports:
            # Add to map
            pass

        template_values = {
            'google_api_key': GOOGLE_API_KEY,
            'waypoints': getWaypoints()
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/get-status', GetStatus),
        ('/report', SetStatus),
        ('/upload', UploadWaypoints),
        ('/delete-waypoints', DeleteWaypoints),
        ('/add-waypoints', AddWaypoint),
        ('/plot-report', PlotReports),
        ('/delete-reports', DeleteReports)
        ], debug=True)
