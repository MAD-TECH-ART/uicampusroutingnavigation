/* Browser location adapter. Coordinates remain client-side. */
(function (global) {
  class BrowserLocationAdapter {
    constructor() {
      this.watchId = null;
    }

    normalizePosition(position) {
      return {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        heading: position.coords.heading,
        speed: position.coords.speed,
        timestamp: position.timestamp,
      };
    }

    normalizeError(error) {
      return {
        code: {
          1: "PERMISSION_DENIED",
          2: "POSITION_UNAVAILABLE",
          3: "TIMEOUT",
        }[error.code] || "UNKNOWN",
        message: error.message || "Unable to determine the current location.",
      };
    }

    request(onSuccess, onError) {
      if (!navigator.geolocation) {
        onError({ code: "UNSUPPORTED", message: "Location is not supported by this browser." });
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => onSuccess(this.normalizePosition(position)),
        (error) => onError(this.normalizeError(error)),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    }

    startWatching(onSuccess, onError) {
      if (!navigator.geolocation) {
        onError({ code: "UNSUPPORTED", message: "Location is not supported by this browser." });
        return false;
      }
      this.stopWatching();
      this.watchId = navigator.geolocation.watchPosition(
        (position) => onSuccess(this.normalizePosition(position)),
        (error) => onError(this.normalizeError(error)),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 3000 }
      );
      return true;
    }

    stopWatching() {
      if (this.watchId !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(this.watchId);
        this.watchId = null;
      }
    }

    isWatching() {
      return this.watchId !== null;
    }
  }

  global.BrowserLocationAdapter = BrowserLocationAdapter;
})(window);
