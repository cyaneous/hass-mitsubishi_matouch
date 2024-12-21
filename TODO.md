# TODO

- report unavailable if we havent been able to connect x number of times/seconds or minutes since last time
- use a data update coordinator?

# CODE

self._last_updated = datetime.utcfromtimestamp(0)
self._last_updated = datetime.now()
if self._last_updated < datetime.now() - timedelta(minutes=1):
