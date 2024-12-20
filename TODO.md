# TODO

- fix dry setpoint adjustment
- use big endian for some fields???
- clean up / general error handling
- report unavailable if we havent been able to connect x number of times/seconds or minutes since last time

# FUTURE

- use a data update coordinator?

# CODE

self._last_updated = datetime.utcfromtimestamp(0)
self._last_updated = datetime.now()
if self._last_updated < datetime.now() - timedelta(minutes=1):
