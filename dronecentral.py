import abc
import cgi
import webapp2
from google.appengine.api import urlfetch
from google.appengine.ext import db

DEFAULT_SURVEY_NAME = "ACTIVE SURVEY"

GCM_SERVER = "https://android.googleapis.com/gcm/send"
GOOGLE_API_KEY = "AIzaSyBVM4ZyBqaxCdLBb2zjkoJhjn-oLeenuJQ"
REGISTRATION_ID = "Registration Id of the target device"


MAIN_PAGE_HTML = """\
<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="initial-scale=1.0, user-scalable=no" />
    <style type="text/css">
      html { height: 100% }
      body { height: 100%; margin: 0; padding: 0 }
      #map-canvas { height: 100% }
    </style>
    <script type="text/javascript" src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBes8BF3izsF6xmMAkqFl5LOFKXOcYcswU&sensor=true">
    </script>
    <script type="text/javascript">
      function initialize() {
        var mapOptions = {
          center: new google.maps.LatLng(-34.397, 150.644),
          zoom: 8,
          mapTypeId: google.maps.MapTypeId.ROADMAP
        };
        var map = new google.maps.Map(document.getElementById("map-canvas"),
            mapOptions);
      }
      google.maps.event.addDomListener(window, 'load', initialize);
    </script>
  </head>
  <body>
    <H1> Drone central </H1>
    <div id="map-canvas" style="width: 80%; height: 60%"></div>

    <H3> Display waypoints </H3>
    <span style="float:left;">
      <form enctype="multipart/form-data" action="/upload" method="post" >
        <input type="file" name="waypoint-file" />
        <input type="submit" value = "Upload waypoints"/>
      </form>
    </span>

    <form action="/delete-waypoints" method="post">
      <div><input type="submit" value="Delete waypoints"></div>
    </form>


    <H3> Send command </H3>
    <form action="/get-status" method="post">
      <div><text name="lat" rows="3" cols="60" value="1.0"></text></div>
      <div><text name="lon" rows="3" cols="60" value="1.0"></text></div>
      <div><input type="submit" value="Get status"></div>
    </form>
    <form action="/add-waypoint" method="post">
      <div><text name="wp_lat" rows="3" cols="60" value="1.0"></text></div>
      <div><text name="wp_lon" rows="3" cols="60" value="1.0"></text></div>
      <div><input type="submit" value="Add waypoint"></div>
    </form>


    <H3> Send report </H3>
    <form action="/report" method="post">
      Battery status: <input type="text" name="battery_status" size=3>
      Turn-rate: <input type="text" name="turn_rate" size=3>
      Heading: <input type="text" name="heading" size=3>
      Speed: <input type="text" name="speed" size=3>
      Lat:  <input type="text" name="lat" size=8> 
      Lon:  <input type="text" name="lon" size=8>
      <div><input type="submit" value="Report"></div>
    </form>
  </body>
</html>
"""


def survey_key(survey_name=DEFAULT_SURVEY_NAME):
    """
    Constructs a Datastore key for a Survey entity
    with survey_name.
    """
    return db.Key(survey_name)


class StatusReport(db.Model):
    """Models a drone status report"""
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
        query = WaypointList.all()
        waypoint_lists = query.fetch(10)

        for wp_list in waypoint_lists:
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
        report.speed = float(self.request.get('speed'))
        report.heading = float(self.request.get('heading'))
        report.turn_rate = float(self.request.get('turn_rate'))
        report.battery_status = int(float(self.request.get('battery_status')))
        report.put()
        #query_params = {'survey_name': survey_name}
        #self.redirect('/?' + urllib.urlencode(query_params))


class MainPage(webapp2.RequestHandler):

    def get(self):
        """Write main page"""
        survey_name = self.request.get('survey_name',
                                          DEFAULT_SURVEY_NAME)

        report_query = StatusReport.all()

        reports = report_query.fetch(100)

        for report in reports:
            # Add to map
            pass

        self.response.write(MAIN_PAGE_HTML)

application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/get-status', GetStatus),
        ('/report', SetStatus),
        ('/upload', UploadWaypoints),
        ('/delete-waypoints', DeleteWaypoints),
        ('/add-waypoint', AddWaypoint),
        ('/plot-waypoints', PlotWaypoints),
        ('/plot-report', PlotReports)
        ], debug=True)
