#!/usr/bin/python
import pdb
import time, sys
from datetime import timedelta, date, datetime
import time
import re
import subprocess
from operator import itemgetter, attrgetter, methodcaller

from optparse import OptionParser,OptionValueError

import fileinput
import os.path

import ezstatslib
from ezstatslib import Team,Player
from ezstatslib import enum,checkNew,htmlLink
from ezstatslib import NEW_GIF_TAG as newGifTag

import HTML

def fillH2H(who,whom,minute):
    try:
        for elem in headToHead[who]:
            if elem[0] == whom:
                elem[1] += 1
                elem[2][minute] += 1
    except Exception, ex:
        ezstatslib.logError("fillH2H: who=%s, whom=%s, minute=%d, ex=%s\n" % (who, whom, minute, ex))
            
def clearZeroPlayer(pl):
    # TODO remove from headToHead
    
    # clear battle progress
    for mpline in matchProgress: # mpline: [[pl1_name,pl1_frags],[pl2_name,pl2_frags],..]
        for mp in mpline:        # mp:     [pl1_name,pl1_frags]
            if pl.name == mp[0]:
                mpline.remove(mp)       # TODO REMOVE
                                        # (n for n in n_list if n !=3)  # ifilter
                                        # https://docs.python.org/2.7/library/stdtypes.html#mutable-sequence-types
        

usageString = "" 
versionString = ""
parser = OptionParser(usage=usageString, version=versionString)

parser.add_option("-f",   action="store",       dest="inputFile",      type="str",  metavar="LOG_FILE", help="")
parser.add_option("--league", action="store",   dest="leagueName",     type="str",  metavar="LEAGUE",   help="")
parser.add_option("--scripts", action="store_false",   dest="withScripts", default=True,   help="")

# TODO add -q option: without output at all

(options, restargs) = parser.parse_args()

if not options.leagueName:
    options.leagueName = "";

# check rest arguments
if len(restargs) != 0:
    parser.error("incorrect parameters count(%d)" % (len(restargs)))
    exit(0)

#f = open(options.inputFile, "r")
#f = fileinput.input(options.inputFile)

if options.inputFile:
    f = fileinput.input(options.inputFile)
else:
    f = sys.stdin

matchdate = ""
mapName = ""
matchlog = [[]]
isStart = False
isEnd = False

allplayers = []
disconnectedplayers = []
dropedplayers = []
spectators = []

readLinesNum = 0

newLogFormat = False # if at least one LOG_TIMESTAMP_DELIMITER in logs

#line = f.readline()
#readLinesNum += 1
line,readLinesNum = ezstatslib.readLineWithCheck(f, readLinesNum)

#while not "matchdate" in line:
#    line = f.readline()
#matchdate = line.split("matchdate: ")[1].split("\n")[0]

while not ezstatslib.isMatchStart(line):
    if ".mvd" in line:
        mapName = line.split("]")[0]
        mapName += "]"
    
    if "telefrag" in line and not "teammate" in line: # telefrags before match start
        matchlog[0].append(line)

    if "matchdate" in line:
        if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:  # TODO TIME
            matchStartStamp = int( line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[0] )
            line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
            
        matchdate = line.split("matchdate: ")[1].split("\n")[0]            

#    line = f.readline()
#    readLinesNum += 1
    line,readLinesNum = ezstatslib.readLineWithCheck(f, readLinesNum)

matchMinutesCnt = 1
# line = f.readline()
# readLinesNum += 1
while not ezstatslib.isMatchEnd(line):
    if line != "":
        matchlog[ matchMinutesCnt - 1 ].append(line)
#    line = f.readline()
#    readLinesNum += 1
    line,readLinesNum = ezstatslib.readLineWithCheck(f, readLinesNum)
    
    if not newLogFormat and ezstatslib.LOG_TIMESTAMP_DELIMITER in line:  # TODO TIME
        newLogFormat = True
    
    # rea[rbf] left the game with 23 frags
    if "left the game" in line:
        lineStriped = line
        lineStamp = -1
        if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:  # TODO TIME
            lineStriped    = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
            lineStamp = int( line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[0] )
        
        plname = lineStriped.split(" ")[0];
        pl = Player( "", plname, 0, 0, 0 )  #def __init__(self, teamname, name, score, origDelta, teamkills):
        pl.isDropped = True
        if lineStamp != -1:
            pl.disconnectTime = lineStamp - matchStartStamp
        dropedplayers.append(pl);  # TODO record number of frags for final output

    # Majority votes for mapchange
    if "Majority votes for mapchange" in line:
        #print "Majority votes for mapchange"
        ezstatslib.logError("Majority votes for mapchange\n")
        exit(1)
        
    # Match stopped by majority vote
    if "Match stopped by majority vote" in line:
        #print "Match stopped by majority vote"
        ezstatslib.logError("Match stopped by majority vote\n")
        exit(1)
        
    if "remaining" in line or "overtime" in line:  # [9] minutes remaining
        matchMinutesCnt += 1
        matchlog.append([])

while not "Player statistics" in line:
#    line = f.readline()
#    readLinesNum += 1
    line,readLinesNum = ezstatslib.readLineWithCheck(f, readLinesNum)
    

line = f.readline()  # (=================================)
line = f.readline()  # Frags (rank) . efficiency
line = f.readline()
readLinesNum += 3

while not "top scorers" in line and not "Running" in line:
    if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:  # TODO TIME
        line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]
    
    playerName = line.split(' ')[1].split(':')[0]  # zrkn:

    if playerName[0] == "_":
        playerName = playerName[1:]
        disconnectedplayers.append(playerName)


    line = f.readline()    # "  45 (2) 51.1%"
    readLinesNum += 1

    stats = line.split(' ')

    pl = Player( "", playerName, int(stats[2]), int( stats[3].split('(')[1].split(')')[0]), 0 )  #def __init__(self, teamname, name, score, origDelta, teamkills):
    pl.initPowerUpsByMinutes(matchMinutesCnt)
            
    line = f.readline() # Wp: rl52.1% sg12.2%
    readLinesNum += 1

    pl.parseWeapons(line)

    line = f.readline() # RL skill: ad:82.2 dh:25
    readLinesNum += 1
    pl.rlskill_ad = float(line.split("ad:")[1].split(" ")[0])
    pl.rlskill_dh = float(line.split("dh:")[1].split(" ")[0])

    line = f.readline() # Armr&mhs: ga:0 ya:4 ra:1 mh:1
    readLinesNum += 1
    
    if not "Armr&mhs" in line:
        line = f.readline()
        readLinesNum += 1
    
    pl.ga = int(line.split("ga:")[1].split(" ")[0])
    pl.ya = int(line.split("ya:")[1].split(" ")[0])
    pl.ra = int(line.split("ra:")[1].split(" ")[0])
    pl.mh = int(line.split("mh:")[1].split(" ")[0])

    line = f.readline() # Damage: Tkn:4279 Gvn:4217 Tm:284
    readLinesNum += 1
    pl.tkn = int(line.split("Tkn:")[1].split(" ")[0])
    pl.gvn = int(line.split("Gvn:")[1].split(" ")[0])
    pl.tm  = int(line.split("Tm:")[1].split(" ")[0])

    line = f.readline() # quad

    line = f.readline() # Streaks: Frags:3 QuadRun:0
    readLinesNum += 1
    
    if "Streaks" in line:
        pl.streaks = int(line.split("Streaks: Frags:")[1].split(" ")[0])

    line = f.readline() # SpawnFrags: 4
    readLinesNum += 1
    
    if "OverTime" in line:
        line = f.readline()
        readLinesNum += 1
    
    pl.spawnfrags = int(line.split("SpawnFrags: ")[1].split(" ")[0])

    allplayers.append(pl)

    while not "#" in line:
        if "top scorers" in line or "Running" in line:
            break;
        else:
            #line = f.readline()
            #readLinesNum += 1
            line,readLinesNum = ezstatslib.readLineWithCheck(f, readLinesNum)

# check droped players and add them to allplayers collection
for pl1 in dropedplayers:
    exist = False
    for pl2 in allplayers: 
        if pl1.name == pl2.name:
            exist = True
    if not exist:
        pl1.initPowerUpsByMinutes(matchMinutesCnt)
        allplayers.append(pl1);


# map name
#while not "top scorers" in line:
#    line = f.readline()

if ezstatslib.LOG_TIMESTAMP_DELIMITER in line:  # TODO TIME
    line = line.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]

if mapName == "":
    mapName = line.split(" ")[0]

f.close()

# check that there are more than 1 players
if len(allplayers) == 0:
    #print "No players at all"
    ezstatslib.logError("No players at all\n")
    exit(1)

if len(allplayers) == 1:
    #print "Only one player:", allplayers[0].name
    ezstatslib.logError("Only one player: %s\n" % (allplayers[0].name))
    exit(1)

# head-to-head stats init
# TODO make separate function
headToHead = {}
for pl1 in allplayers:
    headToHead[pl1.name] = []
    for pl2 in allplayers:
        headToHead[pl1.name].append([pl2.name,0,[0 for i in xrange(matchMinutesCnt+1)]])

matchProgress = []  # [[[pl1_name,pl1_frags],[pl2_name,pl2_frags],..],[[pl1_name,pl1_frags],[pl2_name,pl2_frags],..]]
matchProgressDict = []
matchProgressDictEx = []
matchProgressDictEx2 = []
currentMinute = 1
currentMatchTime = 0
battleProgressExtendedNextPoint = (int)(60 / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)

for matchPart in matchlog:
    if not newLogFormat:
        partSize = len(matchPart) - 1  # line about minute change is substracted
        currentPartNum = 0
        timeMult = 0 if partSize == 0 else (60.0 / float(partSize))
         
        battleProgressExtendedPoints = [partSize     / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY,
                                        partSize * 2 / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY,
                                        partSize * 3 / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY]
    
    for logline in matchPart:
        if logline == "":
            continue
        
        if ezstatslib.LOG_TIMESTAMP_DELIMITER in logline:  # TODO TIME
            if len(logline.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)) >= 2:
                lineStamp = int( logline.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[0] )
                logline = logline.split(ezstatslib.LOG_TIMESTAMP_DELIMITER)[1]                
            else:
                ezstatslib.logSkipped("problem with timestamp: " + logline)
                continue
        
            currentMatchTime = lineStamp - matchStartStamp
        elif not newLogFormat:
            currentMatchTime = ((currentMinute - 1) * 60) + int( float(currentPartNum) * timeMult )
        else:
            ezstatslib.logError("Strange line: " + logline);
            continue            

        if not newLogFormat:            
            currentPartNum += 1
        
            # extended match progress
            if currentPartNum in battleProgressExtendedPoints:
                allplayersByFrags = sorted(allplayers, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
                progressLineDict = {}
                for pl in allplayersByFrags:
                    progressLineDict[pl.name] = [pl.frags(), pl.calcDelta()];
                matchProgressDictEx.append(progressLineDict)        
    
        # connected after the match start players
        # 1479137838 <-> Onanim entered the game
        if "entered the game" in logline:            
            connectedPlName = logline.split(" ")[0]
            for pl in allplayers:
                if pl.name == connectedPlName and \
                   not pl.isDropped and \
                   pl.connectTime == 0 and \
                   pl.kills == 0 and pl.deaths == 0:
                    pl.connectTime = currentMatchTime
    
        # battle progress
        if "remaining" in logline or "overtime" in logline:  # [9] minutes remaining                            
            currentMinute += 1            
            #allplayersByFrags = sorted(allplayers, key=methodcaller("frags"), reverse=True)
            allplayersByFrags = sorted(allplayers, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
            progressLine = []
            progressLineDict = {}
            for pl in allplayersByFrags:
                progressLine.append([pl.name, pl.frags()]);
                progressLineDict[pl.name] = [pl.frags(), pl.calcDelta()];
            matchProgress.append(progressLine)
            matchProgressDict.append(progressLineDict)
            matchProgressDictEx.append(progressLineDict)
            battleProgressExtendedNextPoint += (int)(60 / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
            
            if "overtime" in logline:
                if len(allplayersByFrags) >= 2:
                    if allplayersByFrags[0].frags() == allplayersByFrags[1].frags():
                        allplayersByFrags[0].overtime_frags = allplayersByFrags[0].frags()
                        allplayersByFrags[1].overtime_frags = allplayersByFrags[1].frags()
                    else:
                        ezstatslib.logError("ERROR: overtime calculation: currentMinute: %d, allplayersByFrags[0].frags(): %d, allplayersByFrags[1].frags(): %d" % \
                         (currentMinute, allplayersByFrags[0].frags(), allplayersByFrags[1].frags()))
            
            continue
        else:
            if newLogFormat and currentMatchTime > battleProgressExtendedNextPoint:
                battleProgressExtendedNextPoint += (int)(60 / ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
                allplayersByFrags = sorted(allplayers, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
                progressLineDict = {}
                for pl in allplayersByFrags:
                    progressLineDict[pl.name] = [pl.frags(), pl.calcDelta()];
                matchProgressDictEx.append(progressLineDict)
                        
        if not newLogFormat:
            # final time correction
            if currentMatchTime > matchMinutesCnt*60:
                currentMatchTime = matchMinutesCnt*60;                
    
        if len(matchProgressDictEx2) == 0 or matchProgressDictEx2[len(matchProgressDictEx2)-1][allplayers[0].name][0] != currentMatchTime:
            allplayersByFrags = sorted(allplayers, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)
            progressLineDict = {}
            for pl in allplayersByFrags:
                progressLineDict[pl.name] = [currentMatchTime, pl.frags()];
            matchProgressDictEx2.append(progressLineDict)
    
        # telefrag
        checkres,who,whom = ezstatslib.talefragDetection(logline, [])
        if checkres:
            isFoundWho = False if who != "" else True
            isFoundWhom = False
            for pl in allplayers:
                if who != "" and pl.name == who:
                    pl.incKill(currentMatchTime, who, whom)
                    pl.tele_kills += 1
                    isFoundWho = True
    
                if pl.name == whom:
                    pl.incDeath(currentMatchTime, who, whom)
                    pl.tele_deaths += 1
                    isFoundWhom = True
    
            if who != "":
                fillH2H(who,whom,currentMinute)
    
            if not isFoundWho or not isFoundWhom:
                #print "ERROR: count telefrag", who, "-", whom, ":", logline
                ezstatslib.logError("ERROR: count telefrag %s-%s: %s\n" % (who, whom, logline))
                exit(0)
    
            continue
    
        checkres,checkname = ezstatslib.suicideDetection(logline)
        if checkres:
            isFound = False
            for pl in allplayers:
                if pl.name == checkname:                
                    pl.incSuicides(currentMatchTime)
                    fillH2H(checkname,checkname,currentMinute)
                    isFound = True
                    break;
            if not isFound:
                #print "ERROR: count suicides"
                ezstatslib.logError("ERROR: count suicides\n")
                exit(0)
    
            continue    
        
        # power ups
        checkres,checkname,pwr = ezstatslib.powerupDetection(logline)
        if checkres:
            isFound = False
            for pl in allplayers:
                if pl.name == checkname:                    
                    exec("pl.inc%s(%d,%d)" % (pwr, currentMinute, currentMatchTime))
                    isFound = True
                    break;
            if not isFound:
                ezstatslib.logError("ERROR: powerupDetection: no playername %s\n" % (checkname))
                exit(0)
    
            continue
    
        # spectator detection
        if "Spectator" in logline: # Spectator zrkn connected
            spectators.append(logline.split(" ")[1])
            continue
    
        cres,who,whom,weap = ezstatslib.commonDetection(logline)
    
        if cres:
            if not weap in ezstatslib.possibleWeapons:
                #print "ERROR: unknown weapon:", weap
                ezstatslib.logError("ERROR: unknown weapon: %s\n" % (weap))
                exit(0)
    
            isFoundWho = False
            isFoundWhom = False
            for pl in allplayers:
                if pl.name == who:
                    pl.incKill(currentMatchTime, who, whom);
                    exec("pl.%s_kills += 1" % (weap))
                    isFoundWho = True
                
                if pl.name == whom:
                    pl.incDeath(currentMatchTime, who, whom);
                    exec("pl.%s_deaths += 1" % (weap))
                    isFoundWhom = True
            
            fillH2H(who,whom,currentMinute)
    
            if not isFoundWho or not isFoundWhom:
                ezstatslib.logError("ERROR: count common %s-%s: %s\n" % (who, whom, logline))
    
            continue            

# all log lines are processed

# check that there at least one kill
killsSumOrig = 0
killsSum     = 0
for pl in allplayers:
    killsSumOrig += pl.origScore;
    killsSum     += pl.kills;
if killsSumOrig == 0 and killsSum == 0:
    ezstatslib.logError("There are no kills\n")
    exit(1)

# clear players with 0 kills and 0 deaths
# TODO change progressSrt structure to be able to clean zero players in battle progress (source data: zero_player_in_stats)
# TODO clear headToHead of zero player
for pl in allplayers:
    if pl.kills == 0 and pl.deaths == 0:
        allplayers.remove(pl);

allplayersByFrags = sorted(allplayers, key=lambda x: (x.frags(), x.kills, x.calcDelta()), reverse=True)

# fill final battle progress
progressLine = []
progressLineDict = {}
for pl in allplayersByFrags:    
    progressLine.append([pl.name, pl.frags()]);
    progressLineDict[pl.name] = [pl.frags(), pl.calcDelta()];
matchProgress.append(progressLine)
matchProgressDict.append(progressLineDict)
matchProgressDictEx.append(progressLineDict)

minsCount = len(matchProgressDict)
progressLineDict = {}
for pl in allplayersByFrags:
    progressLineDict[pl.name] = [minsCount*60, pl.frags()];

# correct final point if necessary
if len(matchProgressDictEx2) != 0 and matchProgressDictEx2[len(matchProgressDictEx2)-1][allplayers[0].name][0] == minsCount*60:
    matchProgressDictEx2[len(matchProgressDictEx2)-1] = progressLineDict
else:
    matchProgressDictEx2.append(progressLineDict)
    
# fill final element in calculatedStreaks
for pl in allplayers:
    pl.fillStreaks(currentMatchTime)
    pl.fillDeathStreaks(currentMatchTime)

plNameMaxLen = ezstatslib.DEFAULT_PLAYER_NAME_MAX_LEN
for pl in allplayers:
    plNameMaxLen = max(plNameMaxLen, len(pl.name))

powerUpsStatus = {}
for pwrup in ["ra","ya","ga","mh"]:
    exec("powerUpsStatus[\"%s\"] = False" % (pwrup))

# move power stats for doroped players from power ups by minutes and get power ups status
for pl in allplayers:
    pl.recoverArmorStats()

    for pwrup in ["ra","ya","ga","mh"]:
        exec("if pl.%s != 0:\n    powerUpsStatus[\"%s\"] = True" % (pwrup, pwrup))
    
# achievements
for pl in allplayers:
    pl.calculateAchievements(matchProgress, powerUpsStatus, headToHead, isTeamGame = False)
    
ezstatslib.calculateCommonAchievements(allplayers, headToHead, isTeamGame = False)
    
# generate output string
resultString = ""

resultString += "\n================== " + options.leagueName + " ==================\n"
resultString += "matchdate: " + matchdate + "\n"
resultString += "map: " + mapName + "\n"
resultString += "\n"

for pl in allplayersByFrags:
    resultString += ("{0:%ds} {1:3d}    ({2:s})\n" % (plNameMaxLen)).format(pl.name, pl.calcDelta(), pl.getFormatedStats_noTeamKills())

# if options.withScripts:
#     resultString += "</pre>MAIN_STATS_PLACE\n<pre>"
    
if options.withScripts:
    resultString += "</pre>MAIN_STATS_BARS_PLACE\n<pre>"
    
if options.withScripts:
    resultString += "</pre>PLAYERS_ACHIEVEMENTS_PLACE\n<pre>"

resultString += "\n"
resultString += "Power ups:\n"
for pl in allplayersByFrags:
    resultString += ("{0:%ds}  {1:s}\n" % (plNameMaxLen)).format(pl.name, pl.getFormatedPowerUpsStats())

# all players
resultString += "\n"
resultString += "All players:\n"
resultString += "GreenArm:   " + " [ " + ezstatslib.sortPlayersBy(allplayers, "ga") + " ]\n"
resultString += "YellowArm:  " + " [ " + ezstatslib.sortPlayersBy(allplayers, "ya") + " ]\n"
resultString += "RedArm:     " + " [ " + ezstatslib.sortPlayersBy(allplayers, "ra") + " ]\n"
resultString += "MegaHealth: " + " [ " + ezstatslib.sortPlayersBy(allplayers, "mh") + " ]\n"
resultString += "\n"
resultString += "TakenDam:   " + " [ " + ezstatslib.sortPlayersBy(allplayers, "tkn") + " ]\n"
resultString += "GivenDam:   " + " [ " + ezstatslib.sortPlayersBy(allplayers, "gvn") + " ]\n"
resultString += "DeltaDam:   " + " [ " + ezstatslib.sortPlayersBy(allplayers,"damageDelta", fieldType="method") + " ]\n"
resultString += "\n"
resultString += "Kills:      " + " [ " + ezstatslib.sortPlayersBy(allplayers, "kills") + " ]\n"
resultString += "Deaths:     " + " [ " + ezstatslib.sortPlayersBy(allplayers, "deaths") + " ]\n"
resultString += "Suicides:   " + " [ " + ezstatslib.sortPlayersBy(allplayers, "suicides") + " ]\n"
resultString += "\n"
resultString += "Streaks:    " + " [ " + ezstatslib.sortPlayersBy(allplayers,"streaks") + " ]\n"
resultString += "SpawnFrags: " + " [ " + ezstatslib.sortPlayersBy(allplayers,"spawnfrags") + " ]\n"
resultString += "\n"
resultString += "RL skill DH:" + " [ " + ezstatslib.sortPlayersBy(allplayers, "rlskill_dh") + " ]\n"
resultString += "RL skill AD:" + " [ " + ezstatslib.sortPlayersBy(allplayers, "rlskill_ad") + " ]\n"
resultString += "\n"
# resultString += "Weapons:\n"
# resultString += "RL:         " + " [ " + ezstatslib.sortPlayersBy(allplayers, "w_rl", units="%") + " ]\n"
# resultString += "LG:         " + " [ " + ezstatslib.sortPlayersBy(allplayers, "w_lg", units="%") + " ]\n"
# resultString += "GL:         " + " [ " + ezstatslib.sortPlayersBy(allplayers, "w_gl", units="%") + " ]\n"
# resultString += "SG:         " + " [ " + ezstatslib.sortPlayersBy(allplayers, "w_sg", units="%") + " ]\n"
# resultString += "SSG:        " + " [ " + ezstatslib.sortPlayersBy(allplayers, "w_ssg", units="%") + " ]\n"
resultString += "\n"

resultString += "Players weapons:\n"
weaponsCheck = ezstatslib.getWeaponsCheck(allplayers)
for pl in allplayersByFrags:
    resultString += ("{0:%ds} kills  {1:3d} :: {2:100s}\n" % (plNameMaxLen)).format(pl.name, pl.kills, pl.getWeaponsKills(pl.kills, weaponsCheck))
    resultString += ("{0:%ds} deaths {1:3d} :: {2:100s}\n" % (plNameMaxLen)).format("",      pl.deaths, pl.getWeaponsDeaths(pl.deaths, weaponsCheck))
    resultString += "\n"
    
# ============================================================================================================

# # calculated streaks
# resultString += "\n"
# resultString += "Players streaks (%d+):\n" % (ezstatslib.KILL_STREAK_MIN_VALUE)
# resultString += str( ezstatslib.createStreaksHtmlTable(allplayers, ezstatslib.StreakType.KILL_STREAK) )
# resultString += "\n"
# 
# # death streaks
# resultString += "\n"
# resultString += "Players death streaks (%d+):\n" % (ezstatslib.DEATH_STREAK_MIN_VALUE)
# resultString += str( ezstatslib.createStreaksHtmlTable(allplayers, ezstatslib.StreakType.DEATH_STREAK) )
# resultString += "\n"

totalStreaksHtmlTable = \
    HTML.Table(header_row=["Kill streaks (%d+)\n" % (ezstatslib.KILL_STREAK_MIN_VALUE), "Death streaks (%d+)\n" % (ezstatslib.DEATH_STREAK_MIN_VALUE)],
               rows=[ \
                   HTML.TableRow(cells=[ \
                                     HTML.TableCell( str( ezstatslib.createStreaksHtmlTable(allplayersByFrags, ezstatslib.StreakType.KILL_STREAK)) ),
                                     HTML.TableCell( str( ezstatslib.createStreaksHtmlTable(allplayersByFrags, ezstatslib.StreakType.DEATH_STREAK)) ) \
                                       ] \
                                ) \
                    ],               
               border="1", 
               style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")

resultString += "\n"
resultString += "Players streaks:\n"
resultString += str(totalStreaksHtmlTable)
resultString += "\n"


fullTotalStreaksHtmlTable = \
    HTML.Table(header_row=["Kill streaks (%d+)\n" % (ezstatslib.KILL_STREAK_MIN_VALUE), "Death streaks (%d+)\n" % (ezstatslib.DEATH_STREAK_MIN_VALUE)],
               rows=[ \
                   HTML.TableRow(cells=[ \
                                     HTML.TableCell( str( ezstatslib.createFullStreaksHtmlTable(allplayersByFrags, ezstatslib.StreakType.KILL_STREAK)) ),
                                     HTML.TableCell( str( ezstatslib.createFullStreaksHtmlTable(allplayersByFrags, ezstatslib.StreakType.DEATH_STREAK)) ) \
                                       ] \
                                ) \
                    ],               
               border="1", 
               style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")

# POINT: Players full streaks
# resultString += "\n"
# resultString += "Players full streaks:\n"
# resultString += str(fullTotalStreaksHtmlTable)
# resultString += "\n"

# POINT: streaks timelines place
# if options.withScripts:
#     resultString += "</pre>STREAK_TIMELINE_PLACE\n<pre>"
#     
if options.withScripts:
    resultString += "</pre>STREAK_ALL_TIMELINE_PLACE\n<pre>"

# ============================================================================================================

# H2H stats
resultString += "\n"
resultString += "Head-to-Head stats (who :: whom)\n"
for pl in allplayersByFrags:
    resStr = ""
    for el in sorted(headToHead[pl.name], key=lambda x: x[1], reverse=True):
        resStr += "%s%s(%d)" % ("" if resStr == "" else ", ", el[0], el[1])
    resultString += ("{0:%ds} {1:3d} :: {2:100s}\n" % (plNameMaxLen)).format(pl.name, pl.kills, resStr)
resultString += "\n"

# ============================================================================================================

# Players duels table
resultString += "\n"
resultString += "Players duels:<br>"
headerRow=['', 'Frags', 'Kills', 'Deaths']
playersNames = []
for pl in allplayersByFrags:
    headerRow.append(pl.name);
    playersNames.append(pl.name)

colAlign=[]
for i in xrange(len(headerRow)):
    colAlign.append("center")

htmlTable = HTML.Table(header_row=headerRow, border="2", cellspacing="3", col_align=colAlign,
                       style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")

for pl in allplayersByFrags:
    tableRow = HTML.TableRow(cells=[ezstatslib.htmlBold(pl.name),
                                    ezstatslib.htmlBold(pl.frags()),
                                    ezstatslib.htmlBold(pl.kills),
                                    ezstatslib.htmlBold(pl.deaths)])
        
    for plName in playersNames:
        if pl.name == plName:
            tableRow.cells.append( HTML.TableCell(str(pl.suicides), bgcolor=ezstatslib.BG_COLOR_GRAY) )
        else:            
            plKills = 0
            for val in headToHead[pl.name]:
                if val[0] == plName:
                    plKills = val[1]
            
            plDeaths = 0
            for val in headToHead[plName]:
                if val[0] == pl.name:
                    plDeaths = val[1]
            
            cellVal = "%s / %s" % (ezstatslib.htmlBold(plKills)  if plKills  > plDeaths else str(plKills),
                                   ezstatslib.htmlBold(plDeaths) if plDeaths > plKills  else str(plDeaths))
            
            cellColor = ""
            if plKills == plDeaths:
                cellColor = ezstatslib.BG_COLOR_LIGHT_GRAY
            elif plKills > plDeaths:
                cellColor = ezstatslib.BG_COLOR_GREEN
            else:
                cellColor = ezstatslib.BG_COLOR_RED
            
            tableRow.cells.append( HTML.TableCell(cellVal, bgcolor=cellColor) )
            
    htmlTable.rows.append(tableRow)  

resultString += str(htmlTable)
    
i = 1
resultString += "\n\n"
resultString += "battle progress:\n"
plPrevFragsDict = {}

isFirstLine = True
for mpline in matchProgress: # mpline: [[pl1_name,pl1_frags],[pl2_name,pl2_frags],..]       
    s = ""
    for mp in mpline:        # mp:     [pl1_name,pl1_frags]
        if isFirstLine:
            plFragsDelta = mp[1]
        else:
            plFragsDelta = mp[1] - plPrevFragsDict[mp[0]]
        
        plPrevFragsDict[mp[0]] = mp[1]

        if plFragsDelta == 0:
            deltaStr = "<sup>0  </sup>"
        else:
            if plFragsDelta > 0:
                deltaStr = "<sup>+%d%s</sup>" % (plFragsDelta, " " if plFragsDelta < 10 else "")
            else:
                deltaStr = "<sup>%d%s</sup>"  % (plFragsDelta, " " if plFragsDelta < 10 else "")
        
        s += ("{0:%ds}" % (plNameMaxLen+9+11)).format( "%s(%d)%s" % (mp[0], mp[1], deltaStr) )
    
    if isFirstLine: isFirstLine = False
    
    resultString += "%d:%s %s\n" % (i, "" if i >= 10 else " ",  s)
    i += 1
    
# POINT battle progress
# if options.withScripts:
#     resultString += "\nBP_PLACE\n"
    
if options.withScripts:
    resultString += "\nHIGHCHART_BATTLE_PROGRESS_PLACE\n"
    
if options.withScripts:
    resultString += "\nHIGHCHART_EXTENDED_BATTLE_PROGRESS_PLACE\n"
    
if options.withScripts:
    resultString += "\nHIGHCHART_PLAYERS_RANK_PROGRESS_PLACE\n"
    
if options.withScripts:
    resultString += ezstatslib.HTML_EXPAND_CHECKBOX_TAG
    for pl in allplayersByFrags:
        resultString += "</pre>%s_KILLS_BY_MINUTES_PLACE\n<pre>" % (ezstatslib.escapePlayerName(pl.name))    

if options.withScripts:
    resultString += "<hr>\n"
    resultString += ezstatslib.HTML_EXPAND_POWER_UPS_CHECKBOX_TAG
    resultString += "</pre> POWER_UPS_BARS_PLACE\n"
    resultString += "\nHIGHCHART_POWER_UPS_PLACE\n<pre>"
    # resultString += "</pre>ra_BY_MINUTES_PLACE\n<pre>"
    # resultString += "</pre>ya_BY_MINUTES_PLACE\n<pre>"
    # resultString += "</pre>ga_BY_MINUTES_PLACE\n<pre>"
    # resultString += "</pre>mh_BY_MINUTES_PLACE\n<pre>"
    for pl in allplayersByFrags:
        resultString += "</pre>%s_POWER_UPS_BY_MINUTES_PLACE\n<pre>" % (ezstatslib.escapePlayerName(pl.name))    

if options.withScripts:
    resultString += "</pre>POWER_UPS_TIMELINE_PLACE\n<pre>"
    
if options.withScripts:
    resultString += "</pre>POWER_UPS_TIMELINE_VER2_PLACE\n<pre>"

if len(dropedplayers) != 0:
    dropedStr = ""
    for pl in dropedplayers:
        dropedStr += "%s(drop time: %d)," % (pl.name, pl.disconnectTime)

    dropedStr = dropedStr[:-1]
    resultString += "Droped players: " + dropedStr + "\n"

if len(spectators) != 0:
    resultString += "Spectators: " + str(spectators) + "\n"

if len(disconnectedplayers) != 0:
    resultString += "\n"
    resultString += "Disconnected players: " + str(disconnectedplayers) + "\n"
    resultString += "\n"
    
connectedPlayersStr = ""
for pl in allplayersByFrags:
    if pl.connectTime != 0:
        connectedPlayersStr += "%s(connect time: %d), " % (pl.name, pl.connectTime)
    
if connectedPlayersStr != "":
    connectedPlayersStr = connectedPlayersStr[:-1]
    resultString += "\n"
    resultString += "Connected players: " + connectedPlayersStr[:-1] + "\n"
    resultString += "\n"

print "currentMinute:", currentMinute
print "matchMinutesCnt:", matchMinutesCnt
for pl in allplayersByFrags:
    for el in headToHead[pl.name]:
        print pl.name, ":", el[0], " - ", el[1], " - ", el[2]
        
    print "%s: ra[%d] %s" % (pl.name, pl.ra, str(pl.raByMinutes))
    print "%s: ya[%d] %s" % (pl.name, pl.ya, str(pl.yaByMinutes))
    print "%s: ga[%d] %s" % (pl.name, pl.ga, str(pl.gaByMinutes))
    print "%s: mh[%d] %s" % (pl.name, pl.mh, str(pl.mhByMinutes))
    
    puStr = ""
    for pu in pl.powerUps:
        puStr += "%s, " % (str(pu))
    print "%s: powerUps: %s" % (pl.name, puStr)
    
    # streaks
    strkStr = ""
    for strk in pl.calculatedStreaks:
        strkStr += "%s [%s], " % (strk.toString(), str(strk.names))
        
    print "%s: streaks: %s" % (pl.name, strkStr)

print resultString

# ============================================================================================================

def writeHtmlWithScripts(f, sortedPlayers, resStr):
    plStr = ""
    for pl in sortedPlayers:
        plStr += "%s(%d) " % (pl.name, pl.frags())
    plStr = plStr[:-1]
    plStr += "\n"        
    f.write("<!--\nGAME_PLAYERS\n" + plStr + "-->\n")        
    
    pageHeaderStr = ezstatslib.HTML_HEADER_SCRIPT_SECTION
    pageTitle = "%s %s %s" % (options.leagueName, mapName, matchdate)  # global values
    pageHeaderStr = pageHeaderStr.replace("PAGE_TITLE", pageTitle)
    pageHeaderStr += ezstatslib.HTML_HEADER_SCRIPT_GOOGLE_CHARTS_LOAD
    
    f.write(pageHeaderStr)
        
    # battle progress -->
    bpFunctionStr = ezstatslib.HTML_SCRIPT_BATTLE_PROGRESS_FUNCTION
    
    columnLines = ""        
    for pl in sortedPlayers:
        columnLines += ezstatslib.HTML_SCRIPT_BATTLE_PROGRESS_ADD_COLUMN_LINE.replace("PLAYER_NAME", pl.name)
    bpFunctionStr = bpFunctionStr.replace("ADD_COLUMN_LINES", columnLines)
    
    rowLines = "[0"
    for k in xrange(len(sortedPlayers)):
        rowLines += ",0"        
    rowLines += "],\n"
    
    minuteNum = 1
    for minEl in matchProgressDict:
        rowLines += "[%d" % (minuteNum)
        for pl in sortedPlayers:
            rowLines += ",%d" % (minEl[pl.name][0])
        rowLines += "],\n"
        minuteNum += 1
        
    rowLines = rowLines[:-1]
     
    bpFunctionStr = bpFunctionStr.replace("ADD_ROWS_LINES", rowLines)       

    # POINT battle progress
    # f.write(bpFunctionStr)
    # <-- battle progress
    
    # main stats -->
    # mainStatsStr = ezstatslib.HTML_SCRIPT_MAIN_STATS_FUNCTION
    # fragsLines    = ""
    # killsLines    = ""
    # deathsLines   = ""    
    # suicidesLines = ""
    # for pl in sortedPlayers:
    #     fragsLines    += "['%s',%d],\n" % (pl.name, pl.frags())
    #     killsLines    += "['%s',%d],\n" % (pl.name, pl.kills)
    #     deathsLines   += "['%s',%d],\n" % (pl.name, pl.deaths)
    #     suicidesLines += "['%s',%d],\n" % (pl.name, pl.suicides)
    # 
    # mainStatsStr = mainStatsStr.replace("ADD_FRAGS_ROWS",    fragsLines)
    # mainStatsStr = mainStatsStr.replace("ADD_KILLS_ROWS",    killsLines)
    # mainStatsStr = mainStatsStr.replace("ADD_DEATHS_ROWS",   deathsLines)
    # mainStatsStr = mainStatsStr.replace("ADD_SUICIDES_ROWS", suicidesLines)
    # 
    # f.write(mainStatsStr)
    # <-- main stats
    
    # main stats bars-->
    isAnnotations = True
    
    mainStatsBarsStr = ezstatslib.HTML_SCRIPT_MAIN_STATS_BARS_FUNCTION
    
    namesLine    = "['Name'"
    fragsLine    = "['Frags'"
    killsLine    = "['Kills'"
    deathsLine   = "['Deaths'"    
    suicidesLine = "['Suicides'"
    
    for pl in sortedPlayers:
        namesLine    += ", '%s'" % (pl.name)
        fragsLine    += ", %d" % (pl.frags())
        killsLine    += ", %d" % (pl.kills)
        deathsLine   += ", %d" % (pl.deaths)
        suicidesLine += ", %d" % (pl.suicides)
        
        if isAnnotations:
            namesLine += ", {type: 'string', role: 'annotation'}"
            fragsLine    += ", '%d'" % (pl.frags())
            killsLine    += ", '%d'" % (pl.kills)
            deathsLine   += ", '%d'" % (pl.deaths)
            suicidesLine += ", '%d'" % (pl.suicides)
                    
    namesLine    += "],\n"
    fragsLine    += "],\n"
    killsLine    += "],\n"
    deathsLine   += "],\n"
    suicidesLine += "]\n"
    
    mainStatsBarsStr = mainStatsBarsStr.replace("ADD_HEADER_ROW", namesLine)
    mainStatsBarsStr = mainStatsBarsStr.replace("ADD_STATS_ROWS", fragsLine + killsLine + deathsLine + suicidesLine)    

    f.write(mainStatsBarsStr)
    # <-- main stats bars
    
    # power ups bars-->            
    isAnnotations = True
    
    powerUpsBarsStr = ezstatslib.HTML_SCRIPT_POWER_UPS_BARS_FUNCTION
    
    namesLine = "['Name'"
    raLine    = "['Red Armor'"
    yaLine    = "['Yellow Armor'"
    gaLine    = "['Green Armor'"    
    mhLine    = "['Mega Health'"
    
    for pl in sortedPlayers:
        namesLine += ", '%s'" % (pl.name)
        raLine    += ", %d" % (pl.ra)
        yaLine    += ", %d" % (pl.ya)
        gaLine    += ", %d" % (pl.ga)
        mhLine    += ", %d" % (pl.mh)
        
        if isAnnotations:
            namesLine += ", {type: 'string', role: 'annotation'}"
            raLine    += ", '%d'" % (pl.ra)
            yaLine    += ", '%d'" % (pl.ya)
            gaLine    += ", '%d'" % (pl.ga)
            mhLine    += ", '%d'" % (pl.mh)
                    
    namesLine += "],\n"
    raLine    += "],\n"
    yaLine    += "],\n"
    gaLine    += "],\n"
    mhLine    += "]\n"
    
    powerUpsBarsStr = powerUpsBarsStr.replace("ADD_HEADER_ROW", namesLine)
    powerUpsBarsStr = powerUpsBarsStr.replace("ADD_STATS_ROWS", raLine + yaLine + gaLine + mhLine)    

    f.write(powerUpsBarsStr)
    # <-- power ups bars
    
    # power ups by minutes -->
    
    # TODO ezstatslib.logError("WARNING: ...") check power ups sum and given value
    
    powerUpsByMinutesStr = ""
    maxValue = 0
    minValue = 0
    maxTotalValue = 0
    minTotalValue = 0
    
    for powerUpName in ["RedArmor","YellowArmor","GreenArmor","MegaHealth"]:
        
        shortName = ""
        if powerUpName == "RedArmor":
            shortName = "ra"
        elif powerUpName == "YellowArmor":
            shortName = "ya"
        elif powerUpName == "GreenArmor":
            shortName = "ga"
        elif powerUpName == "MegaHealth":
            shortName = "mh"
        
        raByMinutesStr = ezstatslib.HTML_SCRIPT_POWER_UPS_BY_MINUTES_FUNCTION
        raByMinutesStr = raByMinutesStr.replace("POWER_UP_NAME", powerUpName)
        
        powerUpByMinutesHeaderStr = "['Minute'"
        for pl in allplayersByFrags:
            powerUpByMinutesHeaderStr += ",'%s'" % (pl.name)
        powerUpByMinutesHeaderStr += "],\n"
        
        raByMinutesStr = raByMinutesStr.replace("ADD_HEADER_ROW", powerUpByMinutesHeaderStr)
        raByMinutesStr = raByMinutesStr.replace("ADD_TOTAL_HEADER_ROW", powerUpByMinutesHeaderStr)
        
        raByMinutesRowsStr = ""
        minut = 1
        #plMaxValue = 0
        #plMinValue = 0
        while minut <= currentMinute:
            raByMinutesRowsStr += "['%d'" % (minut)
            
            for pl in sortedPlayers:
                exec("val = pl.%sByMinutes[minut]" % (shortName))
                raByMinutesRowsStr += ",%d" % (val)
            raByMinutesRowsStr += "],\n"
            
            #plMaxValue = max(plMaxValue, stackSum)
            #plMinValue = min(plMinValue, stackNegVal)
            minut += 1
            
        raByMinutesStr = raByMinutesStr.replace("ADD_STATS_ROWS", raByMinutesRowsStr)
        
        raTotalRowsStr = "[''"
        for pl in sortedPlayers:
            exec("val = pl.%s" % (shortName))
            raTotalRowsStr += ",%d" % (val)
        raTotalRowsStr += "],\n"
            
        raByMinutesStr = raByMinutesStr.replace("ADD_TOTAL_STATS_ROWS", raTotalRowsStr)
    
        powerUpsByMinutesDivTag = ezstatslib.HTML_POWER_UPS_BY_MINUTES_DIV_TAG
        powerUpsByMinutesDivTag = powerUpsByMinutesDivTag.replace("POWER_UP_NAME", powerUpName)
        
        powerUpsByMinutesStr += raByMinutesStr
        
        # powerUpsByMinutesStr = powerUpsByMinutesStr.replace("MIN_VALUE", str(minValue))
        # powerUpsByMinutesStr = powerUpsByMinutesStr.replace("MAX_VALUE", str(maxValue))
        # powerUpsByMinutesStr = powerUpsByMinutesStr.replace("TOTAL_MIN__VALUE", str(minTotalValue))
        # powerUpsByMinutesStr = powerUpsByMinutesStr.replace("TOTAL_MAX__VALUE", str(maxTotalValue))
        powerUpsByMinutesStr = powerUpsByMinutesStr.replace("MIN_VALUE", "0")
        powerUpsByMinutesStr = powerUpsByMinutesStr.replace("MAX_VALUE", "10")
        powerUpsByMinutesStr = powerUpsByMinutesStr.replace("TOTAL_MIN__VALUE", "0")
        powerUpsByMinutesStr = powerUpsByMinutesStr.replace("TOTAL_MAX__VALUE", "10")
        
        # add div
        # resStr = resStr.replace("%s_BY_MINUTES_PLACE" % (shortName), powerUpsByMinutesDivTag)                
    
    # f.write(powerUpsByMinutesStr)
    # <-- power ups by minutes
    
    # highcharts power ups -->
    highchartsPowerUpsFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_POWER_UPS_FUNCTIONS
            
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \    
    
    hcDelim = "}, {\n"
    
    for powerUpName in ["ra","ya","ga","mh"]:    
        rowLines = ""        
        for pl in sortedPlayers:
            if rowLines != "":
                rowLines += hcDelim
            
            rowLines += "name: '%s',\n" % (pl.name)
            rowLines += "data: [0"                
            cnt = 0
            for minNum in xrange(1,matchMinutesCnt+1):  # global matchMinutesCnt
                exec("cnt += pl.%sByMinutes[minNum]" % (powerUpName))
                rowLines += ",%d" % (cnt)
            
            rowLines += "]\n"        
        
        highchartsPowerUpsFunctionStr = highchartsPowerUpsFunctionStr.replace("ADD_STAT_ROWS_%s" % (powerUpName), rowLines)
                
    f.write(highchartsPowerUpsFunctionStr)
    # <-- highcharts power ups
    
    # players power ups by minutes by players -->
    allPlayersPowerUpsByMinutesStr = ""
    maxValue = 0    
    maxTotalValue = 0    
    for pl in allplayersByFrags:
        plNameEscaped = ezstatslib.escapePlayerName(pl.name)
        
        playerPowerUpsByMinutesStr = ezstatslib.HTML_SCRIPT_PLAYER_POWER_UPS_BY_MINUTES_BY_PLAYERS_FUNCTION
        playerPowerUpsByMinutesStr = playerPowerUpsByMinutesStr.replace("PLAYER_NAME", plNameEscaped)
        
        playerPowerUpsByMinutesRowsStr = ""
        minut = 1
        plMaxValue = 0        
        while minut <= currentMinute:
            playerPowerUpsByMinutesRowsStr += "['%d',%d,%d,%d,%d],\n" % (minut, pl.mhByMinutes[minut], pl.gaByMinutes[minut], pl.yaByMinutes[minut], pl.raByMinutes[minut])
            stackSum = pl.raByMinutes[minut] + pl.yaByMinutes[minut] + pl.gaByMinutes[minut] + pl.mhByMinutes[minut]
            plMaxValue = max(plMaxValue, stackSum)
            minut += 1
            
        playerPowerUpsByMinutesStr = playerPowerUpsByMinutesStr.replace("ADD_STATS_ROWS", playerPowerUpsByMinutesRowsStr)
        
        playerPowerUpsTotalRowsStr = "['',%d,%d,%d,%d],\n" % (pl.mh, pl.ga, pl.ya, pl.ra)
        playerPowerUpsByMinutesStr = playerPowerUpsByMinutesStr.replace("ADD_TOTAL_STATS_ROWS", playerPowerUpsTotalRowsStr)
        
        playerPowerUpsByMinutesDivTag = ezstatslib.HTML_PLAYER_POWER_UPS_BY_MINUTES_BY_PLAYERS_DIV_TAG
        playerPowerUpsByMinutesDivTag = playerPowerUpsByMinutesDivTag.replace("PLAYER_NAME", plNameEscaped)
        
        allPlayersPowerUpsByMinutesStr += playerPowerUpsByMinutesStr
        
        # add div
        resStr = resStr.replace("%s_POWER_UPS_BY_MINUTES_PLACE" % (plNameEscaped), playerPowerUpsByMinutesDivTag)
        
        # max & min
        maxValue = max(maxValue, plMaxValue)
        
        # maxTotalValue = max(maxTotalValue, pl.kills)
        #maxTotalValue = max(maxTotalValue, sorted(headToHead[pl.name], key=lambda x: x[1], reverse=True)[0][1])
        maxTotalValue = max(maxTotalValue, pl.mh, pl.ga, pl.ya, pl.ra)
            
    allPlayersPowerUpsByMinutesStr = allPlayersPowerUpsByMinutesStr.replace("MAX_VALUE", str(maxValue))    
    allPlayersPowerUpsByMinutesStr = allPlayersPowerUpsByMinutesStr.replace("TOTAL_MAX__VALUE", str(maxTotalValue))
    
    f.write(allPlayersPowerUpsByMinutesStr)
    # <-- players power ups by minutes by players
    
    # players kills by minutes -->
    allPlayerKillsByMinutesStr = ""
    maxValue = 0
    minValue = 0
    maxTotalValue = 0
    minTotalValue = 0
    for pl in allplayersByFrags:
        plNameEscaped = ezstatslib.escapePlayerName(pl.name)
        
        playerKillsByMinutesStr = ezstatslib.HTML_SCRIPT_PLAYER_KILLS_BY_MINUTES_FUNCTION
        playerKillsByMinutesStr = playerKillsByMinutesStr.replace("PLAYER_NAME", plNameEscaped)
        
        playerH2hElem = headToHead[pl.name]
        
        playerKillsByMinutesHeaderStr = "['Minute'"
        for el in playerH2hElem:
            playerKillsByMinutesHeaderStr += ",'%s'" % (el[0] if el[0] != pl.name else "suicides")
        playerKillsByMinutesHeaderStr += "],\n"
        playerKillsByMinutesStr = playerKillsByMinutesStr.replace("ADD_HEADER_ROW", playerKillsByMinutesHeaderStr)
        playerKillsByMinutesStr = playerKillsByMinutesStr.replace("ADD_TOTAL_HEADER_ROW", playerKillsByMinutesHeaderStr)
        
        playerKillsByMinutesRowsStr = ""
        minut = 1
        plMaxValue = 0
        plMinValue = 0
        while minut <= currentMinute:
            playerKillsByMinutesRowsStr += "['%d'" % (minut)
            stackSum = 0
            stackNegVal = 0
            for el in playerH2hElem:
                playerKillsByMinutesRowsStr += ",%d" % (el[2][minut] if el[0] != pl.name else -el[2][minut])
                if el[0] != pl.name:
                    stackSum += el[2][minut]
                else:
                    stackNegVal = min(stackNegVal, -el[2][minut])
            playerKillsByMinutesRowsStr += "],\n"
            plMaxValue = max(plMaxValue, stackSum)
            plMinValue = min(plMinValue, stackNegVal)
            minut += 1
        playerKillsByMinutesStr = playerKillsByMinutesStr.replace("ADD_STATS_ROWS", playerKillsByMinutesRowsStr)
        
        playerKillsTotalRowsStr = "[''"
        for el in playerH2hElem:
            playerKillsTotalRowsStr += ",%d" % (el[1] if el[0] != pl.name else -pl.suicides)
        playerKillsTotalRowsStr += "],\n"
        playerKillsByMinutesStr = playerKillsByMinutesStr.replace("ADD_TOTAL_STATS_ROWS", playerKillsTotalRowsStr)
        
        playerKillsByMinutesDivTag = ezstatslib.HTML_PLAYER_KILLS_BY_MINUTES_DIV_TAG
        playerKillsByMinutesDivTag = playerKillsByMinutesDivTag.replace("PLAYER_NAME", plNameEscaped)
        
        allPlayerKillsByMinutesStr += playerKillsByMinutesStr
        
        # add div
        resStr = resStr.replace("%s_KILLS_BY_MINUTES_PLACE" % (plNameEscaped), playerKillsByMinutesDivTag)
        
        # max & min
        maxValue = max(maxValue, plMaxValue)
        minValue = min(minValue, plMinValue)
        
        # maxTotalValue = max(maxTotalValue, pl.kills)
        maxTotalValue = max(maxTotalValue, sorted(headToHead[pl.name], key=lambda x: x[1], reverse=True)[0][1])
        minTotalValue = min(minTotalValue, -pl.suicides)
        
    allPlayerKillsByMinutesStr = allPlayerKillsByMinutesStr.replace("MIN_VALUE", str(minValue))
    allPlayerKillsByMinutesStr = allPlayerKillsByMinutesStr.replace("MAX_VALUE", str(maxValue))
    allPlayerKillsByMinutesStr = allPlayerKillsByMinutesStr.replace("TOTAL_MIN__VALUE", str(minTotalValue))
    allPlayerKillsByMinutesStr = allPlayerKillsByMinutesStr.replace("TOTAL_MAX__VALUE", str(maxTotalValue))
    
    f.write(allPlayerKillsByMinutesStr)
    # <-- players kills by minutes
    
    # streaks timeline -->
    streaksTimelineFunctionStr = ezstatslib.HTML_SCRIPT_STREAK_TIMELINE_FUNCTION
    
    rowLines = ""
    for pl in allplayersByFrags:
        strkRes,maxStrk = pl.getCalculatedStreaksFull()
        for strk in strkRes:
            rowLines += "[ '%s', '%d', new Date(0,0,0,0,%d,%d), new Date(0,0,0,0,%d,%d) ],\n" % (pl.name, strk.count, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60))
            
        if len(strkRes) == 0:
            rowLines += "[ '%s', '', new Date(0,0,0,0,0,0), new Date(0,0,0,0,0,0) ],\n" % (pl.name)  # empty element in order to add player            
        
        # rowLines += "[ '%s', '', new Date(0,0,0,0,10,0), new Date(0,0,0,0,10,0) ],\n" % (pl.name) # TODO change options - need length        
        
    deathRowLines = ""
    for pl in allplayersByFrags:
        strkRes,maxStrk = pl.getDeatchStreaksFull()
        for strk in strkRes:
            deathRowLines += "[ '%s', '%d', new Date(0,0,0,0,%d,%d), new Date(0,0,0,0,%d,%d) ],\n" % (pl.name, strk.count, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60))            
            
        if len(strkRes) == 0:
            deathRowLines += "[ '%s', '', new Date(0,0,0,0,0,0), new Date(0,0,0,0,0,0) ],\n" % (pl.name)  # empty element in order to add player            
        
        # deathRowLines += "[ '%s', '', new Date(0,0,0,0,10,0), new Date(0,0,0,0,10,0) ],\n" % (pl.name) # TODO change options - need length
    
    streaksTimelineFunctionStr = streaksTimelineFunctionStr.replace("ADD_STATS_ROWS", rowLines)
    streaksTimelineFunctionStr = streaksTimelineFunctionStr.replace("ADD_DEATH_STATS_ROWS", deathRowLines)       
                
    # TODO calculate height using players count
    # TODO black text color for deaths
    # TODO hints ??
    # TODO correct last events end time (10:01 or 10:02)
    # TODO check on 15 and 20 minutes
    # TODO add finish event or events, the timeline should be full
    # TODO bold players names
    # TODO folding ??
                
    # POINT: streaksTimelineFunctionStr
    # f.write(streaksTimelineFunctionStr)
    # <-- streaks timeline
    
    # all streaks timeline -->
    allStreaksTimelineFunctionStr = ezstatslib.HTML_SCRIPT_ALL_STREAK_TIMELINE_FUNCTION
    
    rowLines = ""
    currentRowsLines = ""
    for pl in sortedPlayers:
        strkRes,maxStrk           = pl.getCalculatedStreaksFull(1)
        for strk in strkRes:
            hintStr = "<p>&nbsp&nbsp&nbsp<b>%d: %s</b>&nbsp&nbsp&nbsp</p>" \
                      "<p>&nbsp&nbsp&nbsp<b>Sum: %s</b>&nbsp&nbsp&nbsp</p><hr>" \
                      "&nbsp&nbsp&nbsp<b>Time:</b>&nbsp%dm %ds - %dm %ds&nbsp<br>" \
                      "<b>&nbsp&nbsp&nbspDuration:</b>&nbsp%d seconds<br>&nbsp" % (strk.count, strk.formattedNames(), strk.formattedNamesSum(), (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60), strk.duration())
            #hintStr = "<p>&nbsp&nbsp&nbsp<b>%s</b>&nbsp&nbsp&nbsp</p><hr>&nbsp&nbsp&nbsp<b>Time:</b>&nbsp%dm %ds - %dm %ds&nbsp<br><b>&nbsp&nbsp&nbspDuration:</b>&nbsp%d seconds<br>&nbsp" % (strk.names, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60), strk.duration())
            rowLines += "[ '%s', '%d', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % ("%s_kills" % (pl.name), strk.count, hintStr, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60))
            
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,0,0,0,1),  new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_kills" % (pl.name))
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_kills" % (pl.name), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt    
        
        deathStrkRes,deathMaxStrk = pl.getDeatchStreaksFull(1)
        for strk in deathStrkRes:
            hintStr = "<p>&nbsp&nbsp&nbsp<b>%d: %s</b>&nbsp&nbsp&nbsp</p>" \
                      "<p>&nbsp&nbsp&nbsp<b>Sum: %s</b>&nbsp&nbsp&nbsp</p><hr>" \
                      "&nbsp&nbsp&nbsp<b>Time:</b>&nbsp%dm %ds - %dm %ds&nbsp<br>" \
                      "<b>&nbsp&nbsp&nbspDuration:</b>&nbsp%d seconds<br>&nbsp" % (strk.count, strk.formattedNames(), strk.formattedNamesSum(), (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60), strk.duration())
            #hintStr = "<p>&nbsp&nbsp&nbsp<b>%s</b>&nbsp&nbsp&nbsp</p><hr>&nbsp&nbsp&nbsp<b>Time:</b>&nbsp%dm %ds - %dm %ds&nbsp<br><b>&nbsp&nbsp&nbspDuration:</b>&nbsp%d seconds<br>&nbsp" % (strk.names, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60), strk.duration())
            rowLines += "[ '%s', '%d', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % ("%s_deaths" % (pl.name), strk.count, hintStr, (strk.start / 60), (strk.start % 60), (strk.end / 60), (strk.end % 60))
            
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_deaths" % (pl.name))  
        currentRowsLines += "[ '%s', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_deaths" % (pl.name), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt        
    
    allStreaksTimelineFunctionStr = allStreaksTimelineFunctionStr.replace("ALL_ROWS", rowLines)
    allStreaksTimelineFunctionStr = allStreaksTimelineFunctionStr.replace("CURRENT_ROWS", currentRowsLines)
    
    allStreaksTimelineDivStr = ezstatslib.HTML_SCRIPT_ALL_STREAK_TIMELINE_DIV_TAG
    timelineChartHeight = (len(allplayersByFrags) * 2 + 1) * (33 if len(allplayersByFrags) >= 4 else 35)
    allStreaksTimelineDivStr = allStreaksTimelineDivStr.replace("HEIGHT_IN_PX", str(timelineChartHeight))
    
    # TODO black text color for deaths
    # TODO hints ??    
    # TODO bold players names
    # TODO folding ??
                    
    f.write(allStreaksTimelineFunctionStr)
    # <-- all streaks timeline
    
    # highcharts battle progress -->
    highchartsBattleProgressFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION
            
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "Battle progress")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Frags")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", "")
        
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \    
    
    hcDelim = "}, {\n"
    rowLines = ""        
    for pl in sortedPlayers:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (pl.name)
        # rowLines += "data: [0"
        rowLines += "data: [[0,0]"
        
        graphGranularity = 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        for minEl in matchProgressDictEx:
            # rowLines += ",%d" % (minEl[pl.name])
            rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][0])  # TODO format, now is 0.500000
            graphGranularity += 1.0 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
            
        rowLines += "]\n"        
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)
    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SORTED)
                
    f.write(highchartsBattleProgressFunctionStr)
    # <-- highcharts battle progress
    
    # highcharts battle extended progress -->
    highchartsBattleProgressFunctionStr = ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("highchart_battle_progress", "highchart_battle_progress_extended")
            
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "Battle progress")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Frags")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "")    
        
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \    
    
    hcDelim = "}, {\n"
    rowLines = ""        
    for pl in sortedPlayers:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (pl.name)
        # rowLines += "data: [0"
        rowLines += "data: [[0,0]"
                
        for minEl in matchProgressDictEx2:            
            rowLines += ",[%d,%d]" % (minEl[pl.name][0], minEl[pl.name][1])  # TODO format, now is 0.500000
            
        rowLines += "]\n"        
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)
        
    tickPositions = ""
    for k in xrange(matchMinutesCnt*60+1):
        if k % 30 == 0:
            tickPositions += "%d," % (k)
            
    xAxisLabels = \
        "labels: {\n" \
        "     formatter: function () {\n" \
        "       return (this.value / 60).toFixed(1).toString()\n" \
        "    },\n" \
        "},\n"
    xAxisLabels += "tickPositions: [%s]\n" % (tickPositions)
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", xAxisLabels)
    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SORTED)
                
    f.write(highchartsBattleProgressFunctionStr)
    # <-- highcharts battle extended progress
    
    # power ups timeline -->
    powerUpsTimelineFunctionStr = ezstatslib.HTML_SCRIPT_POWER_UPS_TIMELINE_FUNCTION
    
    rowLines = ""
    colors = "'gray', "
    for pl in sortedPlayers:
        
        # rowLines += "[ '----> %s <----', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s" % (pl.name))
        rowLines += "[ '----> %s <----', '', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s" % (pl.name))
        
        for pwrup in ["RA","YA","GA","MH"]:
            # rowLines += "[ '%s', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_%s" % (pl.name, pwrup))
            # rowLines += "[ '%s', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_%s" % (pl.name, pwrup), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
            rowLines += "[ '%s', '', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_%s" % (pl.name, pwrup))
            rowLines += "[ '%s', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_%s" % (pl.name, pwrup), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt            

        for pu in pl.powerUps:
            # rowLines += "[ '%s', '%s', new Date(2016,1,1,0,%d,%d),  new Date(2016,1,1,0,%d,%d) ],\n" % \
            #             ("%s_%s" % (pl.name, ezstatslib.powerUpTypeToString(pu.type)), "", ((pu.time-1) / 60), ((pu.time-1) % 60), ((pu.time+1) / 60), ((pu.time+1) % 60))
            
            # TODO check that previous entry is not intersected with the new one: need to store and check lastFinishDate (source data: power_ups_intersection_in_stats)
            
            rowLines += "[ '%s', '', '%s', new Date(2016,1,1,0,%d,%d),  new Date(2016,1,1,0,%d,%d) ],\n" % \
                         ("%s_%s" % (pl.name, ezstatslib.powerUpTypeToString(pu.type)), \
                         " %d min %d sec " % (pu.time / 60, pu.time % 60), \
                         ( ((pu.time-3) if (pu.time-3) >= 0 else 0) / 60), \
                         ( ((pu.time-3) if (pu.time-3) >= 0 else 0) % 60), \
                         ( ((pu.time+3) if (pu.time+3) <= matchMinutesCnt*60 else matchMinutesCnt*60) / 60), \
                         ( ((pu.time+3) if (pu.time+3) <= matchMinutesCnt*60 else matchMinutesCnt*60) % 60) )
            
            # rowLines += "[ '%s', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % \
            #             ("%s" % (pl.name), ezstatslib.powerUpTypeToString(pu.type), ((pu.time-1) / 60), ((pu.time-1) % 60), ((pu.time+1) / 60), ((pu.time+1) % 60))
            # rowLines += "[ '%s', '%s', new Date(2016,1,1,0,%d,%d),  new Date(2016,1,1,0,%d,%d) ],\n" % \
            #             ("%s" % (pl.name), ezstatslib.powerUpTypeToString(pu.type), ((pu.time) / 60), ((pu.time) % 60), ((pu.time) / 60), ((pu.time) % 60))
            
            # if pu.type == ezstatslib.PowerUpType.RA: colors += "'%s', " % ("red")
            # if pu.type == ezstatslib.PowerUpType.YA: colors += "'%s', " % ("yellow")
            # if pu.type == ezstatslib.PowerUpType.GA: colors += "'%s', " % ("green")
            # if pu.type == ezstatslib.PowerUpType.MH: colors += "'%s', " % ("#660066")
                        
        # rowLines += "[ '%s', '', new Date(2016,1,1,0,0,0,0,1),  new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s" % (pl.name))
        # rowLines += "[ '%s', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s" % (pl.name), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
        
        # colors += "'gray'"
    
    powerUpsTimelineFunctionStr = powerUpsTimelineFunctionStr.replace("ALL_ROWS", rowLines)
    # powerUpsTimelineFunctionStr = powerUpsTimelineFunctionStr.replace("COLORS", colors)    
    
    powerUpsTimelineDivStr = ezstatslib.HTML_SCRIPT_POWER_UPS_TIMELINE_DIV_TAG
    powerUpsTimelineChartHeight = (len(sortedPlayers) * 5 + 1) * (33 if len(sortedPlayers) >= 4 else 35)    
    powerUpsTimelineDivStr = powerUpsTimelineDivStr.replace("HEIGHT_IN_PX", str(powerUpsTimelineChartHeight))        
                    
    f.write(powerUpsTimelineFunctionStr)
    # <-- power ups timeline
    
    # power ups timeline ver2 -->
    powerUpsTimelineVer2FunctionStr = ezstatslib.HTML_SCRIPT_POWER_UPS_TIMELINE_VER2_FUNCTION
    
    rowLines = ""
    # colors = "'gray', "
    colors = []
    for col in ["red","yellow","green","#660066"]:
        colors += [col for i in xrange(len(sortedPlayers))]
    colStr = ""
    for col in colors:
        colStr += "'%s'," % (col)
    colStr = colStr[:-1]
    
    for pwrup in ["RA","YA","GA","MH"]:
        for pl in sortedPlayers:
            # rowLines += "[ '%s', '', new Date(2016,1,1,0,0,0,0,1),  new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_%s" % (pl.name, pwrup))
            # rowLines += "[ '%s', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_%s" % (pl.name, pwrup), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
            rowLines += "[ '%s', '', '', new Date(2016,1,1,0,0,0,0,1),  new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_%s" % (pl.name, pwrup))
            rowLines += "[ '%s', '', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_%s" % (pl.name, pwrup), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
    
    for pl in sortedPlayers:
        # for pwrup in ["RA","YA","GA","MH"]:
        #     rowLines += "[ '%s', '', new Date(2016,1,1,0,0,0,0,1), new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s_%s" % (pl.name, pwrup))
        #     rowLines += "[ '%s', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s_%s" % (pl.name, pwrup), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt

        for pu in pl.powerUps:
            # rowLines += "[ '%s', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % \
            #             ("%s_%s" % (pl.name, ezstatslib.powerUpTypeToString(pu.type)), "", ((pu.time-1) / 60), ((pu.time-1) % 60), ((pu.time+2) / 60), ((pu.time+2) % 60))
            rowLines += "[ '%s', '', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % \
                        ("%s_%s" % (pl.name, ezstatslib.powerUpTypeToString(pu.type)), \
                         " %d min %d sec " % (pu.time / 60, pu.time % 60), \
                         ( ((pu.time-3) if (pu.time-3) >= 0 else 0) / 60), \
                         ( ((pu.time-3) if (pu.time-3) >= 0 else 0) % 60), \
                         ( ((pu.time+3) if (pu.time+3) <= matchMinutesCnt*60 else matchMinutesCnt*60) / 60), \
                         ( ((pu.time+3) if (pu.time+3) <= matchMinutesCnt*60 else matchMinutesCnt*60) % 60) )
            
            # rowLines += "[ '%s', '%s', new Date(2016,1,1,0,%d,%d), new Date(2016,1,1,0,%d,%d) ],\n" % \
            #             ("%s" % (pl.name), ezstatslib.powerUpTypeToString(pu.type), ((pu.time-1) / 60), ((pu.time-1) % 60), ((pu.time+1) / 60), ((pu.time+1) % 60))
            # rowLines += "[ '%s', '%s', new Date(2016,1,1,0,%d,%d),  new Date(2016,1,1,0,%d,%d) ],\n" % \
            #             ("%s" % (pl.name), ezstatslib.powerUpTypeToString(pu.type), ((pu.time) / 60), ((pu.time) % 60), ((pu.time) / 60), ((pu.time) % 60))
            
            # if pu.type == ezstatslib.PowerUpType.RA: colors += "'%s', " % ("red")
            # if pu.type == ezstatslib.PowerUpType.YA: colors += "'%s', " % ("yellow")
            # if pu.type == ezstatslib.PowerUpType.GA: colors += "'%s', " % ("green")
            # if pu.type == ezstatslib.PowerUpType.MH: colors += "'%s', " % ("#660066")
                        
        # rowLines += "[ '%s', '', new Date(2016,1,1,0,0,0,0,1),  new Date(2016,1,1,0,0,0,0,2)  ],\n" % ("%s" % (pl.name))
        # rowLines += "[ '%s', '', new Date(2016,1,1,0,%d,0,0,1), new Date(2016,1,1,0,%d,0,0,2) ],\n" % ("%s" % (pl.name), matchMinutesCnt, matchMinutesCnt)  # global value: matchMinutesCnt
        
        # colors += "'gray'"
    
    powerUpsTimelineVer2FunctionStr = powerUpsTimelineVer2FunctionStr.replace("ALL_ROWS", rowLines)
    powerUpsTimelineVer2FunctionStr = powerUpsTimelineVer2FunctionStr.replace("COLORS", colStr)    
    
    powerUpsTimelineVer2DivStr = ezstatslib.HTML_SCRIPT_POWER_UPS_TIMELINE_VER2_DIV_TAG
    powerUpsTimelineVer2ChartHeight = (len(sortedPlayers) * 4 + 1) * (33 if len(sortedPlayers) >= 4 else 35)    
    powerUpsTimelineVer2DivStr = powerUpsTimelineVer2DivStr.replace("HEIGHT_IN_PX", str(powerUpsTimelineVer2ChartHeight))        
                    
    f.write(powerUpsTimelineVer2FunctionStr)
    # <-- power ups timeline ver2
    
    # players achievements -->
    playersAchievementsStr = ezstatslib.HTML_PLAYERS_ACHIEVEMENTS_DIV_TAG    
    cellWidth = "20px"
    achievementsHtmlTable = HTML.Table(border="0", cellspacing="0",
                                       style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt;")
    
    for pl in sortedPlayers:
        if len(pl.achievements) != 0:
            tableRow = HTML.TableRow(cells=[ HTML.TableCell(ezstatslib.htmlBold(pl.name), align="center", width=cellWidth) ])  # TODO player name cell width
            for ach in pl.achievements:
                tableRow.cells.append( HTML.TableCell(ach.generateHtmlEx(), align="center" ) )
            
            achievementsHtmlTable.rows.append(tableRow)
        
    playersAchievementsStr = playersAchievementsStr.replace("PLAYERS_ACHIEVEMENTS_TABLE", str(achievementsHtmlTable) + ezstatslib.Achievement.generateAchievementsLevelLegendTable())
    # <-- players achievements
    
    # highcharts players rank progress -->
    highchartsBattleProgressFunctionStr = (ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION).replace("highchart_battle_progress", "players_rank")

    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("GRAPH_TITLE", "Players ranks")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("Y_AXIS_TITLE", "Rank")
    
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MIN_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("MAX_PLAYER_FRAGS", "")
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("EXTRA_XAXIS_OPTIONS", "")
            
    # " name: 'rea[rbf]',\n" \
    # " data: [0,7,13,18,22,24,29,36,38,42,48]\n" \        
    
    hcDelim = "}, {\n"
    rowLines = ""        
    for pl in allplayersByFrags:
        if rowLines != "":
            rowLines += hcDelim
        
        rowLines += "name: '%s',\n" % (pl.name)        
        rowLines += "data: [[0,0]"
        
        graphGranularity = 1.0*2 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
        k = 1
        while k < len(matchProgressDictEx):
            minEl = matchProgressDictEx[k]
            rowLines += ",[%f,%d]" % (graphGranularity, minEl[pl.name][1])  # TODO format, now is 0.500000
            graphGranularity += 1.0*2 / (float)(ezstatslib.HIGHCHARTS_BATTLE_PROGRESS_GRANULARITY)
            k += 2
        
        rowLines += "]\n"
        
        # add negative zone
        rowLines += ",zones: [{ value: 0, dashStyle: 'Dash' }]"
        
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("ADD_STAT_ROWS", rowLines)    
    # tooltip style
    highchartsBattleProgressFunctionStr = highchartsBattleProgressFunctionStr.replace("TOOLTIP_STYLE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_FUNCTION_TOOLTIP_SORTED)
    
    f.write(highchartsBattleProgressFunctionStr)
    # <-- highcharts players rank progress
    
    # write expand/collapse function
    f.write(ezstatslib.HTML_EXPAND_CHECKBOX_FUNCTION)
    f.write(ezstatslib.HTML_EXPAND_POWER_UPS_CHECKBOX_FUNCTION)
    
    f.write(ezstatslib.HTML_SCRIPT_SECTION_FOOTER)
    
    # add divs
    resStr = resStr.replace("BP_PLACE", ezstatslib.HTML_BATTLE_PROGRESS_DIV_TAG)
    #resStr = resStr.replace("MAIN_STATS_PLACE", ezstatslib.HTML_MAIN_STATS_DIAGRAMM_DIV_TAG)
    resStr = resStr.replace("MAIN_STATS_BARS_PLACE", ezstatslib.HTML_MAIN_STATS_BARS_DIV_TAG)    
    resStr = resStr.replace("PLAYERS_ACHIEVEMENTS_PLACE", playersAchievementsStr)
    resStr = resStr.replace("POWER_UPS_BARS_PLACE", ezstatslib.HTML_POWER_UPS_BARS_DIV_TAG)
    resStr = resStr.replace("STREAK_TIMELINE_PLACE", ezstatslib.HTML_SCRIPT_STREAK_TIMELINE_DIV_TAG)
    resStr = resStr.replace("STREAK_ALL_TIMELINE_PLACE", allStreaksTimelineDivStr)
    # resStr = resStr.replace("HIGHCHART_BATTLE_PROGRESS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_BATTLE_PROGRESS_DIV_TAG)
    resStr = resStr.replace("HIGHCHART_BATTLE_PROGRESS_PLACE", "")
    resStr = resStr.replace("HIGHCHART_EXTENDED_BATTLE_PROGRESS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_EXTENDED_BATTLE_PROGRESS_DIV_TAG)
    resStr = resStr.replace("HIGHCHART_POWER_UPS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_POWER_UPS_DIVS_TAG)
    resStr = resStr.replace("POWER_UPS_TIMELINE_PLACE", powerUpsTimelineDivStr)
    resStr = resStr.replace("POWER_UPS_TIMELINE_VER2_PLACE", powerUpsTimelineVer2DivStr)
    resStr = resStr.replace("HIGHCHART_PLAYERS_RANK_PROGRESS_PLACE", ezstatslib.HTML_SCRIPT_HIGHCHARTS_DEATHMATCH_PLAYERS_RANK_PROGRESS_DIV_TAG)    
    
    f.write(resStr)
    
    f.write(ezstatslib.HTML_PRE_CLOSE_TAG)
    
    # add script section for folding
    f.write(ezstatslib.HTML_BODY_FOLDING_SCRIPT)    
    
    f.write(ezstatslib.HTML_FOOTER_NO_PRE)

# check and write output file
leaguePrefix = ""
if "Premier" in options.leagueName:
    leaguePrefix = "PL_"
if "First" in options.leagueName:
    leaguePrefix = "FD_"
if "Second" in options.leagueName:
    leaguePrefix = "SD_"
if "Number" in options.leagueName:    
    leaguePrefix = "N%s_" % (options.leagueName.split(" ")[1])
 
formatedDateTime = ""

matchdate = matchdate.replace("\n","").replace("\r","")
try:
    formatedDateTime = datetime.strptime(matchdate, '%Y-%m-%d %H:%M:%S %Z').strftime('%Y-%m-%d_%H_%M_%S')
except:
    formatedDateTime = datetime.strptime(matchdate.replace(" CEST",""), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d_%H_%M_%S')

filePath     = leaguePrefix + mapName + "_" + formatedDateTime + ".html"
filePathFull = "../" + filePath

isFileNew = False
if os.path.exists(filePathFull):
    # temp file 
    tmpFilePathFull = "../" + filePath + ".tmp"
    if os.path.exists(tmpFilePathFull):        
        os.remove(tmpFilePathFull)
    
    tmpf = open(tmpFilePathFull, "w")
    
    if not options.withScripts:
        tmpf.write(ezstatslib.HTML_HEADER_STR)
        tmpf.write(resultString)
        tmpf.write(ezstatslib.HTML_FOOTER_STR)
    else:
        writeHtmlWithScripts(tmpf, allplayersByFrags, resultString)  
    
    tmpf.close()
    
    tmpinfo = os.stat(tmpFilePathFull)
    finfo   = os.stat(filePathFull)
    
    isSizesEqual = tmpinfo.st_size == finfo.st_size
    
    if isSizesEqual:
        os.remove(tmpFilePathFull)
    else:
        os.remove(filePathFull)
        os.rename(tmpFilePathFull, filePathFull)

else:  # not os.path.exists(filePathFull):
    outf = open(filePathFull, "w")
    
    if not options.withScripts:
        outf.write(ezstatslib.HTML_HEADER_STR)
        outf.write(resultString)
        outf.write(ezstatslib.HTML_FOOTER_STR)
    else:    
        writeHtmlWithScripts(outf, allplayersByFrags, resultString)
    
    outf.close()
    isFileNew = True
    
# update contents file
logsIndexPath    = "../" + ezstatslib.LOGS_INDEX_FILE_NAME
logsByMapPath    = "../" + ezstatslib.LOGS_BY_MAP_FILE_NAME
tmpLogsIndexPath = "../" + ezstatslib.LOGS_INDEX_FILE_NAME + ".tmp"

files = os.listdir("../")

#headerRow = HTML.TableRow(["Date", "Time", "Premier League", "First Division", "Second Division"], header=True)

headerRow = HTML.TableRow(cells=[], header=True)
attrs = {} # attribs    
attrs['colspan'] = 2
headerRow.cells.append( HTML.TableCell("Date", header=True) )
headerRow.cells.append( HTML.TableCell("Time", header=True) )
headerRow.cells.append( HTML.TableCell("Premier League", attribs=attrs, header=True) )
headerRow.cells.append( HTML.TableCell("First Division", attribs=attrs, header=True) )
headerRow.cells.append( HTML.TableCell("Second Division", attribs=attrs, header=True) )

filesTable = HTML.Table(header_row=headerRow, border="1", cellspacing="3", cellpadding="8")

filesMap = {}  # key: dt, value: [[ [PL1,dt],[PL2,dt],..],[ [FD1,dt], [FD2,dt],.. ],[ [SD1,dt], [SD2,dt],.. ]]

zerodt = datetime(1970,1,1)
filesMap[zerodt] = [[],[],[]]  # files with problems

otherFiles = []

for fname in files:
    if "html" in fname and len(fname) != 0 and fname[0] == "N":
        logHeadStr = subprocess.check_output(["head", "%s" % ("../" + fname)])
        if "GAME_PLAYERS" in logHeadStr:
            playsStr = logHeadStr.split("GAME_PLAYERS")[1].split("-->")[0]
                
        plays = []
        if playsStr != "":
            playsStr = playsStr.replace("\n","")
            plays = playsStr.split(" ")
        
        otherFiles.append([fname, plays])
        
    
    elif "html" in fname and ("PL" in fname or "FD" in fname or "SD" in fname):
                
        #"PL_[dad2]_2016-05-23_18_45_16.html"
        #nameSplit = fname.split("_")  # ['PL', '[dad2]', '2016-05-23', '18', '45', '16.html']
        #dateSplit = nameSplit[2].split("-")        
        
        dateRes = re.search("(?<=]_).*(?=.html)", fname)
                
        if dateRes:
            try:
                dt = datetime.strptime(dateRes.group(0), "%Y-%m-%d_%H_%M_%S")
                dateStruct = datetime.strptime(dateRes.group(0).split("_")[0], "%Y-%m-%d")
            
                if not dateStruct in filesMap.keys(): # key exist
                    filesMap[dateStruct] = [[],[],[]]
                    
                fnamePair = [fname,dt]
                    
                if "PL" in fname:
                    filesMap[dateStruct][0].append(fnamePair)
                elif "FD" in fname:
                    filesMap[dateStruct][1].append(fnamePair)
                else: # SD
                    filesMap[dateStruct][2].append(fnamePair)
            except Exception, ex:
                if "PL" in fname:
                    filesMap[zerodt][0].append(fnamePair)
                elif "FD" in fname:
                    filesMap[zerodt][1].append(fnamePair)
                else: # SD
                    filesMap[zerodt][2].append(fnamePair)
                break;
                
        else: # date parse failed
            if "PL" in fname:
                filesMap[zerodt][0].append(fnamePair)
            if "FD" in fname:
                filesMap[zerodt][1].append(fnamePair)
            else: # SD
                filesMap[zerodt][2].append(fnamePair)
        
        
        # if isFileNew and filePath == fname:
        #     tableRow = HTML.TableRow(cells=[ HTML.TableCell("<a href=\"" + fname + "\">" + fname + "</a>" + newGifTag + "<br>\n") ])
        # else:
        #     tableRow = HTML.TableRow(cells=[ HTML.TableCell("<a href=\"" + fname + "\">" + fname + "</a>" + "<br>\n") ])
        # filesTable.rows.append(tableRow)
        # modTime = os.stat("../" + fname).st_mtime # TODO newGifTag <-> modTime

# IDEA: http://codepen.io/codyhouse/pen/FdkEf
# IDEA: http://codepen.io/jenniferperrin/pen/xfwab

def generateHtmlList(playersNames):
    if len(playersNames) == 0:
        return ""
    
    fontSize = 8
    styleHeightStr = ""
    # workaround for web kit bug with select tag size - size less than 4 is ignored
    if len(playersNames) < 4:
        styleHeightStr = "; height:%dpt" % (fontSize*len(playersNames) + 6)    
    
    htmlList = "<select style=\"font-family: Helvetica; font-size: %dpt%s\" name=\"select\" size=\"%d\" multiple=\"multiple\" title=\"OLOLOLO\">\n" % (fontSize, styleHeightStr, len(playersNames))
    i = 0
    for pl in playersNames:
        htmlList += "<option>%s</option>\n" % (pl)
        #htmlList += "<option%s>%s</option>\n" % (" selected" if i < 2 else "", pl)
        i += 1
        
    htmlList += "</select>\n"
    return htmlList

sorted_filesMap = sorted(filesMap.items(), key=itemgetter(0), reverse=True)

filesByMapDict = {} # key: mapname, value: [ [legue, date, players], ..]

for el in sorted_filesMap: # el: (datetime.datetime(2016, 5, 5, 0, 0), [[], [ ['FD_[spinev2]_2016-05-05_16_12_52.html',dt1], ['FD_[skull]_2016-05-05_13_38_11.html',dt2]]])
    formattedDate = el[0]
    if el[0] != zerodt:
        formattedDate = el[0].strftime("%Y-%m-%d")
    
    pls = el[1][0] # array, val: [str,dt]
    fds = el[1][1] # array, val: [str,dt]
    sds = el[1][2] # array, val: [str,dt]
    
    pls = sorted(pls, key=lambda x: x[1], reverse=True)
    fds = sorted(fds, key=lambda x: x[1], reverse=True)
    sds = sorted(sds, key=lambda x: x[1], reverse=True)
    
    alllist = pls + fds + sds
    alllist = sorted(alllist, key=lambda x: x[1], reverse=True)
    
    #maxcnt = max(len(fds), len(pls), len(sds))
    sumcnt = len(fds) + len(pls) + len(sds)
    
    tableRow = HTML.TableRow(cells=[ HTML.TableCell(formattedDate) ])
    fullTimeRowIndex = len(filesTable.rows)
        
    # TODO checkbox for hiding textareas with players
    # TODO baloons instead of textareas
    # TODO may be textareas are sensible only for several recent matches
    
    i = 0
    TIME_DELTA = 15*60
    isNewRow = True
    rowspanVal = 0
    rowMask = [0,0,0]
    for i in xrange(sumcnt):
        formattedTime = alllist[i][1].strftime("%H-%M-%S")
        formattedTimeNoSec = alllist[i][1].strftime("%H-%M")
        currentMapName = alllist[i][0].split("_")[1]        
        
        if isNewRow:
            rowMask = [0,0,0]
            minTime = alllist[i][1]
            maxTime = alllist[i][1]
                            
            if i != 0:        
                tableRow = HTML.TableRow(cells=[formattedTime])
            else:
                tableRow.cells.append( HTML.TableCell(formattedTime) )
        
            for j in xrange(3):
                tableRow.cells.append( HTML.TableCell("", style="border-right-width:0") )
                tableRow.cells.append( HTML.TableCell("", style="border-left-width:0") )
        
        minTime = min(minTime, alllist[i][1])
        maxTime = max(maxTime, alllist[i][1])
        
        isP = alllist[i][0][0] == "P"
        isF = alllist[i][0][0] == "F"
        isS = alllist[i][0][0] == "S"
        
        # get log players        
        playsStr = ""
        # logf = open("../" + alllist[i][0], "r")
        # linesCnt = 0        
        
        logHeadStr = subprocess.check_output(["head", "%s" % ("../" + alllist[i][0])])
        if "GAME_PLAYERS" in logHeadStr:
            playsStr = logHeadStr.split("GAME_PLAYERS")[1].split("-->")[0]
                
        plays = []
        if playsStr != "":
            playsStr = playsStr.replace("\n","")
            plays = playsStr.split(" ")
        
        if not filesByMapDict.has_key(currentMapName):
            filesByMapDict[currentMapName] = []
            
        filesByMapDict[currentMapName].append([alllist[i][0][0], str(alllist[i][1]), plays, playsStr, alllist[i][0]] )
                
        if isP: insertIndex = len(tableRow.cells) - 6
        if isF: insertIndex = len(tableRow.cells) - 4
        if isS: insertIndex = len(tableRow.cells) - 2
        
        if isP: rowMask[0] = 1
        if isF: rowMask[1] = 1
        if isS: rowMask[2] = 1
        
        tableRow.cells[insertIndex] = HTML.TableCell( htmlLink(alllist[i][0],
                                                     newGifTag if checkNew(isFileNew, filePath, alllist[i][0]) else ""),
                                                     style="border-right-width:0")
        tableRow.cells[insertIndex+1] = HTML.TableCell( generateHtmlList(plays), style="border-left-width:0" )
                        
        # check next
        if i+1 < sumcnt:
            formattedTimeNoSecNext = alllist[i+1][1].strftime("%H-%M")
            currentMapNameNext = alllist[i+1][0].split("_")[1]
            
            if currentMapNameNext == currentMapName \
               and ( int(time.mktime(alllist[i][1].timetuple())) - int(time.mktime(alllist[i+1][1].timetuple())) ) < TIME_DELTA:
                isNewRow = False
            else:
                isNewRow = True
            
            isPNext = alllist[i+1][0][0] == "P"
            isFNext = alllist[i+1][0][0] == "F"
            isSNext = alllist[i+1][0][0] == "S"
                
            if isPNext and rowMask[0] == 1: isNewRow = True
            if isFNext and rowMask[1] == 1: isNewRow = True
            if isSNext and rowMask[2] == 1: isNewRow = True
        else:
            isNewRow = True
        
        if isNewRow:
            # correct time cell
            if minTime != maxTime:
                tableRow.cells[len(tableRow.cells)-7] = "%s\n    - \n%s" % (minTime.strftime("%H-%M-%S"), maxTime.strftime("%H-%M-%S"))
            
            filesTable.rows.append(tableRow)
            rowspanVal += 1
            
        i += 1          
    
    # set rowspan attribute of full time cell
    if rowspanVal != 0:
        attrs = {} # attribs
        attrs['rowspan'] = rowspanVal
        filesTable.rows[fullTimeRowIndex].cells[0].attribs = attrs
        
            
        # if isP:
        #     tableRow.cells.append( HTML.TableCell( htmlLink(alllist[i][0],
        #                                            newGifTag if checkNew(isFileNew, filePath, alllist[i][0]) else ""),
        #                                            style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell( generateHtmlList(plays), style="border-left-width:0" ) )
        #     tableRow.cells.append( HTML.TableCell("", style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-left-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-left-width:0") )
        #     
        # if isF:
        #     tableRow.cells.append( HTML.TableCell("", style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-left-width:0") )
        #     tableRow.cells.append( HTML.TableCell( htmlLink(alllist[i][0],
        #                                            newGifTag if checkNew(isFileNew, filePath, alllist[i][0]) else ""),
        #                                            style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell( generateHtmlList(plays), style="border-left-width:0" ) )
        #     tableRow.cells.append( HTML.TableCell("", style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-left-width:0") )
        # 
        # if isS:
        #     tableRow.cells.append( HTML.TableCell("", style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-left-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell("", style="border-left-width:0") )
        #     tableRow.cells.append( HTML.TableCell( htmlLink(alllist[i][0],
        #                                            newGifTag if checkNew(isFileNew, filePath, alllist[i][0]) else ""),
        #                                            style="border-right-width:0") )
        #     tableRow.cells.append( HTML.TableCell( generateHtmlList(plays), style="border-left-width:0" ) )
        #     
        # filesTable.rows.append(tableRow)
        # i += 1
    
    # i = 0
    # for i in xrange(maxcnt):
    #     if i != 0:
    #         tableRow = HTML.TableRow(cells=[])
    #     
    #     if i < len(pls): # PLs
    #         tableRow.cells.append( HTML.TableCell( htmlLink(pls[i][0],
    #                                                newGifTag if checkNew(isFileNew, filePath, pls[i][0]) else "") ) )
    #     else: # no PLs
    #         tableRow.cells.append( HTML.TableCell("") )
    #         
    #     if i < len(fds): # FDs
    #         tableRow.cells.append( HTML.TableCell( htmlLink(fds[i][0],
    #                                                newGifTag if checkNew(isFileNew, filePath, fds[i][0]) else "") ) )            
    #     else: # no FDs
    #         tableRow.cells.append( HTML.TableCell("") )
    #         
    #     if i < len(sds): # SDs
    #         tableRow.cells.append( HTML.TableCell( htmlLink(sds[i][0],
    #                                                newGifTag if checkNew(isFileNew, filePath, sds[i][0]) else "") ) )            
    #     else: # no SDs
    #         tableRow.cells.append( HTML.TableCell("") )
    #         
    #     filesTable.rows.append(tableRow)
    #     i += 1

filesByMapTable = HTML.Table(border="1", cellspacing="1", style="font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 8pt;")

for filemap in filesByMapDict.keys():
    maxCnt = 0
    
    tableRow = HTML.TableRow(cells=[])
        
    tableRow.cells.append( HTML.TableCell("%s(%d)" % (filemap, len(filesByMapDict[filemap])), align="center") )
        
    for el in filesByMapDict[filemap]:
        maxCnt = max(maxCnt, len(el[2]))    
        tableRow.cells.append( HTML.TableCell("<a href=\"%s\">%s %s</a>" % (el[4], ezstatslib.htmlBold(el[0]), el[1]), align="center") )
    
    filesByMapTable.rows.append( tableRow )
        
    for cnt in xrange(maxCnt):
        tRow = HTML.TableRow(cells=[""])
                
        for el in filesByMapDict[filemap]:
            tRow.cells.append( HTML.TableCell("%s" % (el[2][cnt] if len(el[2]) > cnt else ""), align="center") )
        
        filesByMapTable.rows.append( tRow )

logsf = open(logsByMapPath, "w")
logsf.write(ezstatslib.HTML_HEADER_STR)
logsf.write(str(filesByMapTable))
logsf.write(ezstatslib.HTML_FOOTER_STR)
logsf.close()


logsf = open(tmpLogsIndexPath, "w")
logsf.write(ezstatslib.HTML_HEADER_STR)
logsf.write(htmlLink(ezstatslib.TOURNAMENT_TABLE_FILE_NAME, linkText = "AdRiver Quake tournament 2016"))
logsf.write("<hr>")
logsf.write(htmlLink(ezstatslib.LOGS_BY_MAP_FILE_NAME, linkText = "Match results by maps"))
logsf.write("<hr>")
logsf.write(htmlLink(ezstatslib.TEAM_LOGS_INDEX_FILE_NAME, linkText = "Team matches logs"))
logsf.write("<hr>")
logsf.write(str(filesTable))

logsf.write("<hr>")
logsf.write("<h1>Duels</h1>")
for fileName in otherFiles:
    logsf.write( htmlLink(fileName[0], isBreak = False) )
    logsf.write( generateHtmlList(fileName[1]) )
logsf.write("<hr>")

logsf.write(ezstatslib.HTML_FOOTER_STR)
logsf.close()

if os.path.exists(logsIndexPath):
    os.remove(logsIndexPath)
os.rename(tmpLogsIndexPath, logsIndexPath)

print filePath    
