import logging
import MySQLdb
import re
import sys

from shared_python import Args, Common
from shared_python.Sql import Sql

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
log = logging.getLogger()

def clean_and_load_data(args):
	# Initialize DB
	sql = Sql(args)

	## Purge working DB to an empty state
	# Unfortunately, we have to use python string interpolation
	# because the pymysql driver unilaterally quotes args passed
	# in.
	sql.execute("DROP DATABASE {}".format(args.temp_db_database))
	sql.execute("CREATE DATABASE {}".format(args.temp_db_database))

	log.info("Loading database file {}".format(args.db_input_file))
	sql.run_script_from_file(args.db_input_file, args.temp_db_database, '', True)
	log.info("Database loaded.")

	sql.create_skeleton(args.output_database)

def process_fics(args):
	# First, get a list of all possible fics
	sql = Sql(args)

	possible_fics = sql.execute(
		"""SELECT a.id_topic, b.subject, b.id_member from smf_topics a
		 LEFT JOIN smf_messages b ON a.id_first_msg = b.id_msg
		 WHERE a.id_board IN %s LIMIT 150""",
		[args.rp_forums])

	# Unfortunately, many of these fics are not actually fics, but
	# just other posts in the RP fora.  I've looked at some of the
	# other metadata (locked posts, stickied posts, etc.), but at
	# least in the archive that I'm using to write this, none of
	# them are reliable. We're going to have to sort through them
	# and make some educated guesses, and hope that gives the
	# tagging folx enough of a filtration that they can get the
	# scragglers.

	for fic in possible_fics:
		log.debug(fic)
		title = fic[1]
		author = fic[2]

		# Nibble away at the title slowly
		(genre, title) = get_genre(title)
		(rating, title) = get_rating(title)
		(status, title) = get_status(title)

		# Now that we have everything useful out, strip
		# everything after the first tag tombstone (excluding
		# the genre, which doesn't insert one)
		pos = title.find("\x1D")
		if pos != -1:
			title = title[:pos]
		title = title.strip()

		print(u"Final title is: '{}'".format(title))
		print(u"Genre is: '{}'".format(genre))
		print(u"Rating is: '{}'".format(rating))
		print(u"Status is: '{}'".format(status))

def get_genre(title):
	genres = {
		"riddick":"Riddick",
		"rid slash":"Riddick",
		"rid":"Riddick",
		"tcor":"The Chronicles of Riddick",
		"cor":"The Chronicles of Riddick",
		"pb":"Pitch Black",
		"kag":"Knockaround Guys",
		"xxx":"xXx",
		"ama":"A Man Apart",
		"pacifier":"The Pacifier",
		"paci":"The Pacifier",
		"br":"Boiler Room",
		"a man apart":"A Man Apart",
		"bad":"Babylon A.D.",
		"original":"Original Work",
		"orig":"Original Work",
		"ori":"Original Work",
		"hitman":"Hitman"
	}

	return tag_search(genres, title, '')

def get_rating(title):
	ratings = {
		"g":"General Audiences",
		"pg":"Teen And Up Audiences",
		"pg-13":"Teen And Up Audiences",
		"pg13":"Teen And Up Audiences",
		"pg 13":"Teen And Up Audiences",
		"r":"Mature",
		"nc17":"Explicit",
		"nc-17":"Explicit",
		"nc 17":"Explicit",
		"x":"Explicit"
	}

	return tag_search(ratings, title)

def get_status(title):
	statuses = {
		"ong":False,
		"wip":False,
		"fin":True
	}

	return tag_search(statuses, title)

def tag_search(pat_dict, title, tombstone = "\x1D"):
	pattern = r"|".join(pat_dict.keys())
	mat = re.search(r"[\(\[\{\s](" + pattern + r")[\)\]\}$]", title.lower())
	if mat:
		tag = pat_dict[mat.group(1)]
		new_title = title[:mat.start()] + tombstone + title[mat.end():]
		return (tag, new_title)
	else:
		return (None, title)

# Temp Main
args = Args.args_for_01()
process_fics(args)
