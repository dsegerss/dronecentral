import os
import webapp2
import jinja2
import logging
from google.appengine.api import urlfetch
from google.appengine.ext import db

DEFAULT_SURVEY_NAME = "ACTIVESURVEY"
GCM_SERVER = "https://android.googleapis.com/gcm/send"
GOOGLE_API_KEY = "AIzaSyBes8BF3izsF6xmMAkqFl5LOFKXOcYcswU"

MIN_RUDDER_ANGLE = -90
MAX_RUDDER_ANGLE = 90
MIN_LOAD = 0
MAX_LOAD = 100

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def num_in_range(val, min_val, max_val):
    try:
        load = float(val)
        if load >= min_val and load <= max_val:
            return True
    except:
        return False


def survey_key(survey_name=DEFAULT_SURVEY_NAME):
    """
    Constructs a Datastore key for a Survey entity
    with survey_name.
    """
    return db.Key.from_path('WaypointList', survey_name)


class Device(db.Model):
    device_id = db.StringProperty(indexed=False)


class StatusReport(db.Model):
    """Models a drone status report"""
    operative = db.BooleanProperty(indexed=False)
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


class SendMessage(webapp2.RequestHandler):
    """
    Class containing basic functionality to communicate
    with drone using GCM
    """

    def makeNotification(self, cmd, val, result):
        """ Show notification of sent message and received feedback"""
        self.response.headers['Content-Type'] = 'text/html'
        self.response.set_status(200, "OK" )

        template_values = {
            'cmd': cmd,
            'val': val,
            'content': result.content
        }

        template = JINJA_ENVIRONMENT.get_template('message.html')
        self.response.write(template.render(template_values))


def get_device_id():
    dev_query = Device.all()
    devices = dev_query.fetch(1)
    if len(devices) > 0:
        return devices[0].device_id
    else:
        return None


def getReports():
    report_query = StatusReport.all().order('-reportTime')
    reports = report_query.ancestor(
        survey_key(DEFAULT_SURVEY_NAME)).fetch(10)  # get 10 last reports

    logging.info("Found %i reports in datastore" % len(reports))
    return reports


def getWaypoints():
    """Get waypoints from datastore and return as javascript"""
    query = WaypointList.all()
    wp_list = query.ancestor(survey_key(DEFAULT_SURVEY_NAME)).fetch(1)
    if wp_list != []:
        logging.info("Getting %i waypoints" % len(wp_list[0].waypoints))
        return wp_list[0].waypoints
    else:
        logging.info("No waypoints found in datastore")
        return []

        return []


class RegisterDevice(webapp2.RequestHandler):

    def post(self, device_id):
        dev = Device(device_id=device_id)
        dev.put()
        self.response.write("OK")


class MainPage(webapp2.RequestHandler):

    def render(self, command="", response="", alert="", values=None):
        """Write main page"""

        reports = getReports()
        active = ''
        operative = ''
        autopilot = ''

        if len(reports) > 0:
            last_report = reports[0]
            if last_report.active:
                active = 'checked'

            if last_report.operative:
                operative = 'checked'

            if last_report.autopilot:
                autopilot = 'checked'

        logging.info("render active: " + active)

        template_values = {
            'google_api_key': GOOGLE_API_KEY,
            'waypoints': getWaypoints(),
            'reports': reports,
            'command': command,
            'response': response,
            'min_rudder_angle': MIN_RUDDER_ANGLE,
            'max_rudder_angle': MAX_RUDDER_ANGLE,
            'min_load': MIN_LOAD,
            'max_load': MAX_LOAD,
            'alert': alert,
            'autopilot_state': autopilot,
            'operate_state': operative,
            'active_state': active
        }

        if values is not None:
            for key, val in values.iteritems():
                template_values[key] = val

        template = JINJA_ENVIRONMENT.get_template('index.html')
        return template.render(template_values)

    def delete_reports(self):
        db.delete(StatusReport.all())
        self.response.write(
            self.render(
                alert='<script> alert("Deleted reports from db");</script>'))

    def delete_waypoints(self):
        db.delete(WaypointList.all())
        self.response.write(
            self.render(
                alert='<script> alert("Deleted survey from db");</script>'))

    def upload_file(self):
        self.delete_waypoints()
        f = self.request.POST.get('file').file
        waypoint_string = f.read()
        try:
            waypoints = [map(float, wp.split(',')) for wp in
                         waypoint_string.split("\n")[:-1]]
        except:
            self.response.out.write(
                'Invalid file, should be , separated' +
                'coordinates and no header: %s' % str(waypoints))
            return
        waypoint_list = WaypointList(waypoints=[db.GeoPt(wp[1], wp[0])
                                   for wp in waypoints],
                                     parent=survey_key(DEFAULT_SURVEY_NAME))
        waypoint_list.put()
        logging.info("Stored waypoints in data store")
        self.response.write(
            self.render(
                    alert='<script> alert("Saved file to db");</script>'))

    def upload_waypoints(self):
        self.delete_waypoints()
        waypoint_string = self.request.get("waypoint-list")
        waypoints = [map(float, wp.split(',')) for wp in
                     waypoint_string.split()]
        waypoint_list = WaypointList(waypoints=[db.GeoPt(wp[1], wp[0])
                                                for wp in waypoints],
                                     parent=survey_key(DEFAULT_SURVEY_NAME))

        logging.info("Created wp-list has %i nodes" % len(
                waypoint_list.waypoints))

        waypoint_list.put()
        logging.info("Stored waypoints in data store")
        self.response.write(
            self.render(
                    alert='<script> alert("Saved survey wp to db");</script>'))

    def upload_report(self):
        survey_name = self.request.get('survey_name',
                                       DEFAULT_SURVEY_NAME)

        logging.info("Operative = " +
                      self.request.get('operative', '0').lower())
        logging.info("Active = " +
                      self.request.get('active', '0').lower())
        logging.info("Autopilot = " +
                      self.request.get('autopilot', '0').lower())

        report = StatusReport(
            operative=self.request.get('operative', '0').lower() == '1',
            autopilot=self.request.get('autopilot', '0').lower() == '1',
            active=self.request.get('active', '0').lower() == '1',
            current_waypoint=int(float(self.request.get('cwp', -1))),
            speed=float(self.request.get('speed', -1)),
            heading=float(self.request.get('heading', -1)),
            turn_rate=float(self.request.get('turn_rate', -1)),
            lon=float(self.request.get('lon', -1)),
            lat=float(self.request.get('lat', -1)),
            battery_status=int(float(self.request.get('battery_status', -1))),
            parent=survey_key(survey_name))

        report.put()
        logging.info("Saved report to db")

        self.response.write(
            self.render(
                alert='<script> alert("Saved report wp to db");</script>'),)

    def send_message(self, cmd, val='', collapse_key=None):
        """ Send message using GCM and wait for feedback"""

        device_id = get_device_id()
        logging.info("Device is: " + str(device_id))
        if device_id is None:
            logging.info("opening alert")
            self.response.write(
                self.render(
                    alert='<script> alert("Could not ' +
                    'send message  - No device registered");</script>')
                )
            return

        if collapse_key is not None:
            request = (
                "collapse_key=%s&registration_id=%i&command=%s&value=%s" % (
                    collapse_key,
                    device_id,
                    cmd,
                    val))
        else:
            request = "registration_id=%i&command=%s&value=%s" % (
                device_id,
                cmd,
                val)

        logging.info("Sending GET-STATUS")
        response = urlfetch.fetch(
            url=GCM_SERVER,
            payload=request,
            method=urlfetch.POST,
            headers={'Content-Type':
                         'application/x-www-form-urlencoded;charset=UTF-8',
                     'Authorization': 'key=' + GOOGLE_API_KEY}
            )

        logging.debug("Status is %i" % response.status_code)
        logging.debug("Response is %s" % response.content)
        if response.status_code == 200:
            self.render()
#            self.render(command=cmd, response=result.content,
#                        alert='<script> alert("Sent command ' +
#                        '%s, with value %s");</script>' % (cmd, val))
        else:
            self.render()

    def get_survey(self):
        query = WaypointList.all()
        wp_list = query.ancestor(survey_key(DEFAULT_SURVEY_NAME)).fetch(1)
        out = ""
        if wp_list == []:
            return ""
        wp = wp_list.waypoints
        out += "%f,%f" % (wp[0].lng(), wp[0].lat())
        for i in range(1, len(wp)):
            out += " %f,%f" % (wp[0].lng(), wp[0].lat())
        return out

    def get(self):
        self.response.write(self.render())

    def post(self):
        logging.info("entering main.post")
        do = self.request.get('do')

        if do == 'delete-waypoints':
            logging.info("do=delete-waypoints")
            self.delete_waypoints()

        elif do == 'upload-file':
            logging.info("do=upload-file")
            self.upload_file()

        elif do == 'upload-waypoints':
            logging.info("do=upload-waypoints")
            self.upload_waypoints()

        elif do == 'upload-report':
            logging.info("do=upload-report")
            self.upload_report()

        elif do == 'delete-reports':
            logging.info("do=delete-reports")
            self.delete_reports()

        elif do == 'send-waypoints':
            logging.info('do==send-waypoints')
            self.send_message('ADD_WP', self.request.get('value', ""))

        elif do == 'send-survey':
            logging.info('do==send-survey')
            survey = self.get_survey()
            if survey != []:
                self.send_message('ADD_SURVEY', self.request.get('value', ""))

        elif do == 'get-status':
            logging.info('do==get-status')
            self.send_message('GET_STATUS', collapse_key='GET_STATUS')

        elif do == 'set-load':
            logging.info('do==set-load')
            load = self.request.get('value', None)
            if num_in_range(load, MIN_LOAD, MAX_LOAD):
                self.send_message('SET_LOAD', load)

        elif do == 'set-rudder-angle':
            logging.info('do==set-rudder-angle')
            angle = self.request.get('value', None)
            if num_in_range(angle, MIN_RUDDER_ANGLE, MAX_RUDDER_ANGLE):
                self.send_message('SET_RUDDER', angle)

        elif do == 'shutdown':
            logging.info('do==shutdown')
            self.send_message('SHUTDOWN')

        elif do == 'start-motor':
            logging.info('do==start-motor')
            self.send_message('START_MOTOR')

        elif do == 'stop-motor':
            logging.info('do==stop-motor')
            self.send_message('STOP_MOTOR')

        elif do == 'stop-motor':
            logging.info('do==stop-motor')
            self.send_message('STOP_MOTOR')

        elif do == 'toggle-activate':
            logging.info('do==toggle-activate')
            state = self.request.get('state')
            if state == "yes":
                self.send_message('ACTIVATE')
            else:
                self.send_message('DEACTIVATE')

        elif do == 'toggle-operate':
            logging.info('do==toggle-operate')
            state = self.request.get('state')
            if state == "yes":
                self.send_message('OPERATE')
            else:
                self.send_message("SHUTDOWN")

        elif do == 'toggle-autopilot':
            logging.info('do==toggle-autopilot')
            state = self.request.get('state')
            if state == "yes":

                self.send_message('AUTOPILOT')
            else:
                self.send_message('MANUAL')


application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/send-message', SendMessage),
        ('/register-device', RegisterDevice),
        ], debug=True)


def main():
    logging.getLogger().setLevel(logging.DEBUG)
    webapp2.util.run_wsgi_app(application)


if __name__ == "__main__":
    main()
