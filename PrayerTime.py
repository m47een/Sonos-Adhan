from datetime import date
import requests
import schedule
import time
import json

def restoreZone(zone):
  #get the coordinator
  coordinator = zone.snapGroup.coordinator
  if (coordinator != zone):
    # this zone is NOT the coordinator
    zone.join(coordinator)
  else:
    # this zone was the coordinator so add other members in
    for member in zone.snapGroup.members:
      if member != zone:
        member.join(zone)

    # since this zone was the coordinator, restore the previous state of the zone
    zone.snapMedia.restore(fade=False)


def playPrayer(zone, mediaUri, prayerName, household):
  # play the prayer uri
  zone.play_uri(uri=mediaUri, title=prayerName)
  print("playing for " + prayerName)

  # wait until playback finishes or is paused / stopped
  isplaying = True
  while isplaying:
    time.sleep(1)
    state = zone.get_current_transport_info()['current_transport_state']
    isplaying = state == "PLAYING" or state == "TRANSITIONING"

  for member in zone.group.members:
    member.unjoin()
    
  for zone in reversed(household):
    restoreZone(zone)


def initZones(prayer):
  from soco import SoCo
  from soco.snapshot import Snapshot
  import threading

  prayerName = prayer["name"]
  mediaUri = prayer["file"]

  # get all speakers / zones
  households = {}
  speakers = prayer["speakers"]
  for speaker in speakers:
    zone = SoCo(speaker["ip"])

    if zone.household_id in households:
      households[zone.household_id].append(zone)
    else:
      households[zone.household_id]=[zone]

    # take snapshot of current state
    zone.snapMedia = Snapshot(zone)
    zone.snapMedia.snapshot()

    zone.snapGroup = zone.group

    # pause if playing
    # Each Sonos group has one coordinator only these can play, pause, etc.
    if zone.is_coordinator:
      if not zone.is_playing_tv:  # can't pause TV - so don't try!
        # pause music for each coordinators if playing
        trans_state = zone.get_current_transport_info()
        if trans_state["current_transport_state"] == "PLAYING":
            zone.pause()
    
    zone.unjoin()

    # For every Sonos player set volume and mute for every zone
    zone.volume = speaker["volume"]
    zone.mute = False

    #start making groups here
  coordinators = []
  for household in households.values():
    for idx, zone in enumerate(household):
      if idx == 0:
        coordinator=zone
        coordinators.append(zone)
      else:
        zone.join(coordinator)
  
  for coordinator in coordinators:
    t = threading.Thread(target=playPrayer, args = [coordinator, mediaUri, prayerName, households[coordinator.household_id]])
    t.start()




def getTimings():
  print("timings update started")
  # clear any existing prayers from the schedule as about to be refreshed
  schedule.clear('prayer')

  today = date.today().strftime("%d-%m-%Y")
  lon = conf["timing"]["longitude"]
  lat = conf["timing"]["latitude"]
  method = conf["timing"]["method"]
  school = conf["timing"]["school"]
  timezone = conf["timing"]["timezone"]

  print(today)

  url = f"https://api.aladhan.com/v1/timingsByAddress/{today}?address={lat},{lon}&method={method}&school={school}&timezonestring={timezone}"

  r = requests.get(url)
  timings = r.json()["data"]["timings"]
  
  print(url)
  print(timings)

  for prayer in conf["prayers"]:
    prayerName = prayer["name"]
    #initZones(prayer)
    schedule.every().day.at(timings[prayerName],timezone).do(initZones, prayer).tag('prayer', prayerName)

  print("timings update complete")

#-----------------------------------------
# MAIN ENTER POINT
#-----------------------------------------
print("app started")

with open('./config/config.json', 'r') as configjson:
  conf = json.load(configjson)

print("read config")

# run immetdiately on startup to get timings
getTimings()

# schedule to refresh times
schedule.every().day.at(str(conf["timing"]["updateTime"]), str(conf["timing"]["timezone"])).do(getTimings)

while True:
 schedule.run_pending()
 time.sleep(1)