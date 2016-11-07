import smtplib
import urllib
import urllib2
import datetime
import ast
import traceback

#All 7 of the following values need to be set, see toornament website for details
SENDER = ''
SMTP_USERNAME=''
SMTP_PASSWORD=''

TOORNAMENT_ID = ''
API_KEY = ''
CLIENT_ID = ''
CLIENT_SECRET = ''
#this value starts out empty and is set by the authenticate function
ACCESS_TOKEN = ''

#The matches parameter should be a list of objects(dictionaries) containing data about the matches.
#Each object should have a name and email list for both involved teams, as well as the time of the match.
#This function formats an email based upon which matches are occurring today, and sends the email to all involved players.
def sendEmails(matches):
  recipients=['']
  msg = ''
  for match in matches:
    recipients.extend(match['team1emails'])
    recipients.extend(match['team2emails'])
  if len(recipients) > 0:
    recipients = [x for x in recipients if x is not None]
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(SMTP_USERNAME,SMTP_PASSWORD)
    body = '\r\n'.join((
            "From: %s" % SENDER,
            "BCC: %s" % ', '.join(recipients),
            "Subject: Todays Matches",
            "",
            msg
            ))
    server.sendmail(SENDER, recipients, body)
    server.quit()
  else:
    print 'no recipients'
 
#The web service isn't returning json or xml.  It appears to be returning the data formatted as a javascript object, so I decided to just convert it to python syntax and evaluate the string literally into an object.
def evaluateRaw(raw):
  raw=raw.replace('false', 'False')
  raw=raw.replace('true', 'True')
  raw=raw.replace('null', 'None')
  return ast.literal_eval(raw)
  
#We have to do the oauth v2 athentication in order to get participants emails.  The main goal is to get an access_token to be used in the headers of future web service calls.
def authenticate():
  url='https://api.toornament.com/oauth/v2/token'
  values={'grant_type':'client_credentials', 'client_id':CLIENT_ID, 'client_secret':CLIENT_SECRET}
  data = urllib.urlencode(values)
  req = urllib2.Request(url, data)
  response = urllib2.urlopen(req)
  raw = response.read()
  d = evaluateRaw(raw)
  global ACCESS_TOKEN
  ACCESS_TOKEN = d['access_token']
  
def pullMatches():
  url = 'https://api.toornament.com/v1/tournaments/' + TOORNAMENT_ID + '/matches'
  hdr = {'User-Agent': 'Mozilla/5.0', 'X-Api-Key':API_KEY}
  req = urllib2.Request(url, headers=hdr)
  response = urllib2.urlopen(req)
  raw = response.read()
  return evaluateRaw(raw)  
  
#Basically just parses out the data we care about, and returns a nicely formated dictionary
def parseMatches(matches):
  matchData=[]
  today = datetime.datetime.today()
  for match in matches:
    date = match['date']
    if date is not None:
      #this line assumes eastern time zone in the summer.  Ideally should be changed to work for any time zone.
      d=datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S-0400')
      #we conly care about matches happening today
      if d.year == today.year and d.month == today.month and d.day == today.day:
        teams = match['opponents']
        team1id = teams[0]['participant']['id']
        team2id = teams[1]['participant']['id']
        team1name = teams[0]['participant']['name']
        team2name = teams[1]['participant']['name']
        time = d.strftime('%H:%M')
        data = {'team1id':team1id, 'team2id':team2id, 'team1name':team1name, 'team2name':team2name, 'time':time}
        matchData.append(data)
  return matchData
  
#returns a list of emails accociated with the given team.
def getTeamEmails(teamid):
  url = 'https://api.toornament.com/v1/tournaments/' + TOORNAMENT_ID + '/participants/' + teamid
  hdr = {'User-Agent': 'Mozilla/5.0', 'Host':'api.toornament.com', 'X-Api-Key':API_KEY, 'Authorization':'Bearer ' + ACCESS_TOKEN}
  req = urllib2.Request(url, headers=hdr)
  response = urllib2.urlopen(req)
  raw = response.read()
  data = evaluateRaw(raw)
  emails = []
  emails.append(data['email'])
  for l in data['lineup']:
    if 'email' in l:
      emails.append(l['email'])
  return emails
        
#The matches end point only gave us participant id's, but we can use those to call the participant endpoint to get their email addresses.
def findUserEmails(matchData):
  for match in matchData:
    match['team1emails'] = getTeamEmails(match['team1id'])
    match['team2emails'] = getTeamEmails(match['team2id'])

if __name__ == '__main__':
  try:
    matches = pullMatches()
    matchData = parseMatches(matches)
    authenticate()
    findUserEmails(matchData)
    sendEmails(matchData)
  except Exception as e:
    recipients=[]
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(SMTP_USERNAME,SMTP_PASSWORD)
    server.sendmail(SENDER, recipients, 'The notifier process exited with error: ' + str(e) + '\r\n\r\n' + traceback.format_exc())
    server.quit()
