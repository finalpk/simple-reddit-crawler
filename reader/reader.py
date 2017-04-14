#!/usr/bin/env python
import pymysql
import urllib2
import json
import collections
import types
import time
import datetime
import sys
from pprint import pprint

# ----------------------
# Functions 
# ----------------------

# Show script usage
def showUsage():
	print
	print "Usage:"
	print
	print "- To read all new threads from a subreddit:"
	print "python reader.py /r/yoursubreddithere"
	print
	print "- To get all the comments from the threads read"
	print "python reader.py --get-comments"
	print
	sys.exit()

# Read threads
def readThreads(subreddit, cur):
	newThreads = 0
	existingThreads = 0
	for t in subreddit:
		
		# Get the thread info
		threadId = t['data']['id']
		sub = t['data']['subreddit']
		title = t['data']['title']
		self = t['data']['selftext']
		permalink = t['data']['permalink']
		score = t['data']['score']
		created = t['data']['created_utc']
		url = ""
		author = t['data']['author']
		
		if 'url' in i['data']:
			url = i['data']['url']
		
		# Save it to the database. Duplicate threads will be ignored due to the UNIQUE KEY constraint
		try:
			created = datetime.datetime.fromtimestamp(created).strftime('%Y-%m-%d %H:%M:%S')
			cur.execute("""INSERT INTO threads (id_thread, sub, author, title, self, url, permalink, score, created) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (threadId, sub, author, title, self, url, permalink, int(score), created))
			newThreads += 1
			print "New thread: " + title
		except pymysql.err.IntegrityError as e:
			existingThreads += 1

	# Print a summary
	print "Got " + str(newThreads + existingThreads) + " threads."
	print "Inserted " + str(newThreads) + " new threads"
	print "Found " + str(existingThreads) + " already existing threads"
	
	# Log totals
	global totalNewThreads
	totalNewThreads += newThreads
	global totalExistingThreads
	totalExistingThreads += existingThreads

# Recursive function to read comments
def readComments(obj, threadId, threadUrl, cur):
	newComments = 0
	existingComments = 0
	for i in obj:

		# Basic info, present both in Title and Comment
		commentId = i['data']['id']
		anthor = i['data']['author']
		content = ""
		url = ""
		score = 0
		created = 0
		if 'created_utc' in i['data']:
			created = i['data']['created_utc']
		else:
			print "*** WARNING: created_utc not found in this record -> " + commentId

		# Is it a comment?
		if 'body' in i['data']:

			url = threadUrl + commentId
			content = i['data']['body']
			ups = int(i['data']['ups'])
			downs = int(i['data']['downs'])
			score = ups - downs

		# Or is it the title post?
		elif 'selftext' in i['data']:

			url = i['data']['url']
			content = i['data']['selftext']
			score = i['data']['score']

		# Save!
		try:
			created = datetime.datetime.fromtimestamp(created).strftime('%Y-%m-%d %H:%M:%S')
			cur.execute("""INSERT INTO comments (id_comment, id_thread, author, comment, url, score, created) values (%s, %s, %s, %s, %s, %s)""", (commentId, threadId, author, content, url, int(score), created))
			newComments += 1
		except pymysql.err.IntegrityError as e:
			existingComments += 1

		# Does it have a reply?
		if 'replies' in i['data'] and len(i['data']['replies']) > 0:
			readComments(i['data']['replies']['data']['children'], threadId, threadUrl, cur)

	# Print a Summary
	print "Inserted " + str(newComments) + " new comments"
	print "Found " + str(existingComments) + " already existing comments"
	
	# Log totals
	global totalNewComments
	totalNewComments += newComments
	global totalExistingComments
	totalExistingComments += existingComments

def requestJson(url, delay):
	while True:
		try:
			# Reddit API Rules: "Make no more than thirty requests per minute"
			if delay < 2:
				delay = 2
			time.sleep(delay)

			req = urllib2.Request(url, headers=hdr)
			response = urllib2.urlopen(req)
			jsonFile = response.read()
			return json.loads(jsonFile)
		except Exception as e:
			print e

# ----------------------
# Script begins here
# ----------------------

# Setup ------------------------------------------

# Url, header and request delay
# If we don't set an unique User Agent, Reddit will limit our requests per hour and eventually block them
userAgent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36"
if userAgent == "":
	print
	print "Error: you need to set an User Agent inside this script"
	print
	sys.exit()
hdr = {'User-Agent' : userAgent}
baseUrl = "http://www.reddit.com"

# Read args
shouldReadComments = False
shouldReadThreads = False
if len(sys.argv) == 2:
	if sys.argv[1] == "--get-comments":
		shouldReadThreads = True
		delay = 2
		print "Reading comments"
	else:
		subreddit = sys.argv[1]
		sort = sys.argv[2]
		subredditUrl = baseUrl + subreddit + "/" + sort + "/.json"
		shouldReadComments = True
		delay = 30
		print "Reading threads from " + subredditUrl
else:
	showUsage()

print "Starting crawler"
print "Press ctrl+c to stop"
print

# Database connection
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='reddit', charset='utf8mb4')
cur = conn.cursor()

# Start! -----------------------------------------
while True:

	# Log starting time
	startingTime = datetime.datetime.now()
	# Totals to log in the database
	totalNewThreads = 0
	totalExistingThreads = 0
	totalNewComments = 0
	totalExistingComments = 0

	# Read threads
	if not shouldReadThreads:

		# Read the Threads
		print "Requesting new threads..."
		jsonObj = requestJson(subredditUrl, delay)

		# Save the threads
		readThreads(jsonObj['data']['children'], cur)
		conn.commit()

	# Read comments
	if not shouldReadComments:
	
		# Get all the threads urls
		cur.execute("SELECT * FROM threads ORDER BY created DESC")
		threads = dict()
		for row in cur.fetchall():
			threads[row[0]] = row[4]

		# Read them all!
		for k, v in threads.iteritems():

			# Prepare the http request
			print
			print "Requesting thread comments..."
			jsonData = requestJson(baseUrl + urllib2.quote(v.encode('utf8')) + ".json", delay)
			
			# Read the Thread
			# 0 = title
			postData = jsonData[0]['data']['children']
			readComments(postData, k, v, cur)
			# 1 = comments
			data = jsonData[1]['data']['children']
			readComments(data, k, v, cur)
			
			# Save!
			conn.commit()

	# Finishing time
	endingTime = datetime.datetime.now()

	# Log this run in the database
	print
	print "Finishing up. Logging this run..."
	if shouldReadComments:
		print "Total new threads: " + str(totalNewThreads)
		print "Total existing threads (skipped, not inserted): " + str(totalExistingThreads)
	if shouldReadThreads:
		print "Total new comments: " + str(totalNewComments)
		print "Total existing comments (skipped, not inserted): " + str(totalExistingComments)
	print "---------------------------------------------------"
	print
	cur.execute("""INSERT INTO logs (startingTime, endingTime, newThreads, ignoredThreads, newComments, ignoredComments) values (%s, %s, %s, %s, %s, %s)""", (startingTime, endingTime, totalNewThreads, totalExistingThreads, totalNewComments, totalExistingComments))
	conn.commit()

# Close the connection
conn.commit()
cur.close()
conn.close()

