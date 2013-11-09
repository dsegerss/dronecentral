import webapp2
from google.appengine.api import urlfetch
#import json

GCM_SERVER = "https://android.googleapis.com/gcm/send"
GOOGLE_API_KEY = "API Key"
REGISTRATION_ID = "Registration Id of the target device"


class SendMessage(webapp2.RequestHandler):

    def makeRequest(self):
        """Create request to GCM"""
        command = "GETSTATUS"
        value = ""
        request = "registration_ids=%i&command=%s&value=%s" % (REGISTRATION_ID,
                                                               command,
                                                               value)
        return request

    def post(self):
        """ Send message using GCM and wait for feedback"""
        self.response.headers['Content-Type'] = 'text/html'
        self.response.set_status(200, "OK" )
        self.response.out.write('<html>')
        self.response.out.write('<head>')
        self.response.out.write('<title>')
        self.response.out.write('Push')
        self.response.out.write('</title>')
        self.response.out.write('</head>')
        self.response.out.write('<body>')

        result = urlfetch.fetch(
            url="GCM_SERVER",
            payload=self.makeRequest(),
            method=urlfetch.POST,
            headers={'Content-Type':
                         'application/x-www-form-urlencoded;charset=UTF-8',
                     'Authorization': 'key=' + GOOGLE_API_KEY}
            )

        self.response.out.write('Server response, status: ' + result.content )
        self.response.out.write('</body>')
        self.response.out.write('</html>')


class MainPage(webapp2.RequestHandler):

    def get(self):
        """Write main page"""
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!')
        self.response.write('Goodbye, World!')

application = webapp2.WSGIApplication(
    [('/', MainPage),
     ('/send', SendMessage)],
    debug=True)
