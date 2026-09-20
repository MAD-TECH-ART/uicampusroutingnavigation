/* Client-only field collection workflow for real campus coordinates. */
(function (global) {
  const STORAGE_KEY = "ui-campus-field-coordinates-v1";

  function validNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function validateRecord(record) {
    if (!record || !validNumber(record.latitude) || !validNumber(record.longitude) ||
        !(record.accuracy === null || validNumber(record.accuracy)) || !validNumber(record.timestamp)) {
      throw new Error("A coordinate record must include numeric latitude, longitude, timestamp, and optional accuracy.");
    }
    if (record.latitude < -90 || record.latitude > 90) throw new Error("Latitude must be between -90 and 90.");
    if (record.longitude < -180 || record.longitude > 180) throw new Error("Longitude must be between -180 and 180.");
    if (record.accuracy < 0) throw new Error("Accuracy cannot be negative.");
    if (!record.source || !record.source_type) throw new Error("A source reference and source type are required.");
    if (!["low", "medium", "high"].includes(record.confidence)) throw new Error("Confidence must be low, medium, or high.");
  }

  class CoordinateCollectionStore {
    constructor(nodes) {
      this.nodes = nodes;
      this.records = this.load();
    }

    load() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
        const valid = {};
        Object.entries(parsed).forEach(([nodeId, record]) => {
          if (this.nodes[nodeId]) {
            try { validateRecord(record); valid[nodeId] = record; } catch (_) { /* ignore stale local data */ }
          }
        });
        return valid;
      } catch (_) {
        return {};
      }
    }

    save(nodeId, record) {
      if (!this.nodes[nodeId]) throw new Error("Unknown campus node.");
      validateRecord(record);
      this.records[nodeId] = record;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.records));
    }

    remove(nodeId) {
      delete this.records[nodeId];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.records));
    }

    clear() {
      this.records = {};
      localStorage.removeItem(STORAGE_KEY);
    }

    exportPayload() {
      const nodes = {};
      Object.entries(this.records).forEach(([nodeId, record]) => {
        nodes[nodeId] = {
          name: this.nodes[nodeId].name,
          category: this.nodes[nodeId].cat,
          ...record,
        };
      });
      return {
        coordinate_source: "field_collected",
        coordinate_status: Object.keys(nodes).length === Object.keys(this.nodes).length ? "complete" : "partial",
        collected_at: new Date().toISOString(),
        nodes,
      };
    }
  }

  class CoordinateCollectionController {
    constructor({nodes, map, adapter, layer, researchCache = {}, minimumAccuracy = 15}) {
      this.nodes = nodes;
      this.map = map;
      this.adapter = adapter;
      this.layer = layer;
      this.researchCache = researchCache;
      this.store = new CoordinateCollectionStore(nodes);
      this.minimumAccuracy = minimumAccuracy;
      this.selectedNodeId = Object.keys(nodes)[0];
      this.pending = null;
      this.bind();
      this.render();
    }

    bind() {
      document.getElementById("collection-node-search").addEventListener("input", (event) => this.renderNodeOptions(event.target.value));
      document.getElementById("collection-node-select").addEventListener("change", (event) => {
        this.selectedNodeId = event.target.value;
        this.pending = null;
        this.render();
      });
      document.getElementById("collection-accuracy-threshold").addEventListener("change", (event) => {
        const value = Number(event.target.value);
        if (Number.isFinite(value) && value > 0) this.minimumAccuracy = value;
        this.renderCapture();
      });
      document.getElementById("capture-gps-btn").addEventListener("click", () => this.capture());
      document.getElementById("accept-coordinate-btn").addEventListener("click", () => this.accept());
      document.getElementById("recapture-coordinate-btn").addEventListener("click", () => this.capture());
      document.getElementById("clear-node-coordinate-btn").addEventListener("click", () => {
        this.store.remove(this.selectedNodeId);
        this.pending = null;
        this.render();
      });
      document.getElementById("review-research-candidate-btn").addEventListener("click", () => this.reviewCandidate());
      document.getElementById("export-coordinates-btn").addEventListener("click", () => this.export());
      document.getElementById("import-coordinates-input").addEventListener("change", (event) => this.import(event));
      document.getElementById("clear-all-coordinates-btn").addEventListener("click", () => {
        if (confirm("Clear all locally collected campus coordinates?")) {
          this.store.clear();
          this.pending = null;
          this.render();
        }
      });
      this.map.on("click", (event) => {
        if (document.getElementById("collection-panel").style.display !== "block") return;
        this.pending = {
          latitude: event.latlng.lat,
          longitude: event.latlng.lng,
          accuracy: null,
          timestamp: Date.now(),
          source: "",
          source_type: "satellite",
          confidence: "medium",
          notes: "",
        };
        this.renderStoredCoordinates();
        L.circle([event.latlng.lat, event.latlng.lng], {
          radius: 12, color: "#D6553F", fillColor: "#D6553F", fillOpacity: .16, weight: 2,
        }).addTo(this.layer);
        L.circleMarker([event.latlng.lat, event.latlng.lng], {
          radius: 8, color: "#FFFFFF", weight: 2, fillColor: "#D6553F", fillOpacity: 1,
        }).bindTooltip(`Review point for ${this.nodes[this.selectedNodeId].name}`).addTo(this.layer);
        this.renderCapture();
      });
    }

    renderNodeOptions(filter = "") {
      const select = document.getElementById("collection-node-select");
      const needle = filter.trim().toLowerCase();
      const ids = Object.keys(this.nodes).filter((id) => {
        const node = this.nodes[id];
        return !needle || id.toLowerCase().includes(needle) || node.name.toLowerCase().includes(needle) || node.cat.toLowerCase().includes(needle);
      });
      select.innerHTML = "";
      ids.forEach((id) => {
        const option = document.createElement("option");
        option.value = id;
        option.textContent = `${id} — ${this.nodes[id].name} (${this.nodes[id].cat})${this.store.records[id] ? " · COLLECTED" : " · NOT COLLECTED"}`;
        select.appendChild(option);
      });
      if (ids.includes(this.selectedNodeId)) select.value = this.selectedNodeId;
      else if (ids.length) this.selectedNodeId = ids[0];
    }

    render() {
      this.renderStoredCoordinates();
      this.renderNodeOptions(document.getElementById("collection-node-search").value);
      const total = Object.keys(this.nodes).length;
      const collected = Object.keys(this.store.records).length;
      const percent = total ? Math.round((collected / total) * 100) : 0;
      const high = Object.values(this.store.records).filter((record) => record.confidence === "high").length;
      const needsReview = Object.values(this.store.records).filter((record) => !record.verified || record.confidence !== "high").length;
      document.getElementById("collection-progress").textContent = `Coordinates reviewed: ${collected} / ${total} · ${percent}%`;
      document.getElementById("collection-remaining").textContent = `Remaining: ${total - collected}`;
      document.getElementById("collection-quality-summary").textContent = `High confidence: ${high} · Needs review: ${needsReview} · Missing: ${total - collected}`;
      document.getElementById("collection-selected-node").textContent = `${this.selectedNodeId} · ${this.nodes[this.selectedNodeId].name} · ${this.nodes[this.selectedNodeId].cat}`;
      const candidate = this.researchCache.queries?.[this.selectedNodeId]?.results?.[0];
      const candidateButton = document.getElementById("review-research-candidate-btn");
      candidateButton.disabled = !candidate;
      document.getElementById("collection-research-candidate").textContent = candidate
        ? `Research candidate: ${candidate.latitude.toFixed(7)}, ${candidate.longitude.toFixed(7)} · ${candidate.source_url} · UNVERIFIED`
        : "No cached remote research candidate for this node.";
      this.renderCapture();
    }

    reviewCandidate() {
      const candidate = this.researchCache.queries?.[this.selectedNodeId]?.results?.[0];
      if (!candidate) return;
      this.pending = {
        latitude: candidate.latitude,
        longitude: candidate.longitude,
        accuracy: null,
        timestamp: Date.now(),
        source: candidate.source_url,
        source_type: "OpenStreetMap",
        confidence: candidate.confidence || "medium",
        notes: candidate.notes || "Remote research candidate; verify against satellite imagery before acceptance.",
      };
      this.renderStoredCoordinates();
      L.circleMarker([candidate.latitude, candidate.longitude], {
        radius: 8, color: "#FFFFFF", weight: 2, fillColor: "#E3A72E", fillOpacity: 1,
      }).bindTooltip(`Research candidate for ${this.nodes[this.selectedNodeId].name}`).addTo(this.layer);
      this.map.setView([candidate.latitude, candidate.longitude], 18);
      this.renderCapture();
    }

    renderStoredCoordinates() {
      this.layer.clearLayers();
      Object.entries(this.store.records).forEach(([nodeId, record]) => {
        const point = [record.latitude, record.longitude];
        L.circleMarker(point, {
          radius: nodeId === this.selectedNodeId ? 8 : 6,
          color: "#FFFFFF",
          weight: 2,
          fillColor: record.confidence === "high" ? "#1B8A8A" : "#E3A72E",
          fillOpacity: 1,
        }).bindTooltip(`${nodeId} · ${this.nodes[nodeId].name}`).addTo(this.layer);
      });
    }

    renderCapture() {
      const status = document.getElementById("collection-status");
      const record = this.pending || this.store.records[this.selectedNodeId];
      document.getElementById("accept-coordinate-btn").disabled = !this.pending;
      document.getElementById("clear-node-coordinate-btn").disabled = !this.store.records[this.selectedNodeId];
      if (!record) {
        status.textContent = "No coordinate captured for this node.";
        status.className = "location-status";
        document.getElementById("collection-capture-details").textContent = "Place a point on the satellite map or capture a browser GPS position, then review it before accepting.";
        return;
      }
      const low = record.accuracy !== null && record.accuracy > this.minimumAccuracy;
      status.textContent = low ? "GPS accuracy is currently low. Move to an open area and capture again." : "Coordinate ready for review.";
      status.className = "location-status " + (low ? "error" : "found");
      const accuracy = record.accuracy === null ? "not provided" : `±${record.accuracy.toFixed(1)} m`;
      document.getElementById("collection-capture-details").textContent =
        `Latitude: ${record.latitude.toFixed(7)}\nLongitude: ${record.longitude.toFixed(7)}\nAccuracy: ${accuracy}\nTimestamp: ${new Date(record.timestamp).toLocaleString()}`;
      document.getElementById("collection-source").value = record.source || "";
      document.getElementById("collection-source-type").value = record.source_type || "satellite";
      document.getElementById("collection-confidence").value = record.confidence || "medium";
      document.getElementById("collection-notes").value = record.notes || "";
    }

    capture() {
      document.getElementById("collection-status").textContent = "Requesting location...";
      this.adapter.request((location) => {
        this.pending = location;
        this.pending.source = "Browser geolocation capture";
        this.pending.source_type = "browser-gps";
        this.pending.confidence = "medium";
        this.pending.notes = "";
        this.renderStoredCoordinates();
        const point = [location.latitude, location.longitude];
        L.circle(point, {radius: location.accuracy, color: "#D6553F", fillColor: "#D6553F", fillOpacity: .16, weight: 2}).addTo(this.layer);
        L.circleMarker(point, {radius: 8, color: "#FFFFFF", weight: 2, fillColor: "#D6553F", fillOpacity: 1})
          .bindTooltip(`Capture for ${this.nodes[this.selectedNodeId].name}`).addTo(this.layer);
        this.map.setView(point, 18);
        this.renderCapture();
      }, (error) => {
        document.getElementById("collection-status").textContent = error.message || "Location unavailable.";
        document.getElementById("collection-status").className = "location-status error";
      });
    }

    accept() {
      if (!this.pending) return;
      this.pending.source = document.getElementById("collection-source").value.trim();
      this.pending.source_type = document.getElementById("collection-source-type").value;
      this.pending.confidence = document.getElementById("collection-confidence").value;
      this.pending.notes = document.getElementById("collection-notes").value.trim();
      this.pending.verified = true;
      this.pending.status = "reviewed";
      try {
        this.store.save(this.selectedNodeId, this.pending);
      } catch (error) {
        document.getElementById("collection-status").textContent = error.message;
        document.getElementById("collection-status").className = "location-status error";
        return;
      }
      this.pending = null;
      this.render();
    }

    export() {
      const blob = new Blob([JSON.stringify(this.store.exportPayload(), null, 2)], {type: "application/json"});
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "ui-campus-field-coordinates.json";
      link.click();
      URL.revokeObjectURL(link.href);
    }

    import(event) {
      const file = event.target.files[0];
      event.target.value = "";
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const payload = JSON.parse(reader.result);
          if (!payload || !payload.nodes || typeof payload.nodes !== "object") throw new Error("Import must contain a nodes object.");
          const imported = {};
          Object.entries(payload.nodes).forEach(([nodeId, record]) => {
            if (!this.nodes[nodeId]) throw new Error(`Unknown node ID: ${nodeId}`);
            if (!Object.prototype.hasOwnProperty.call(record, "accuracy") ||
                !Object.prototype.hasOwnProperty.call(record, "timestamp")) {
              throw new Error(`${nodeId}: accuracy and timestamp are required.`);
            }
            const normalized = {
              latitude: Number(record.latitude), longitude: Number(record.longitude),
              accuracy: record.accuracy === null ? null : Number(record.accuracy), timestamp: Number(record.timestamp),
              source: String(record.source || ""), source_type: String(record.source_type || ""),
              confidence: String(record.confidence || ""), notes: String(record.notes || ""),
              verified: Boolean(record.verified), status: String(record.status || "needs_review"),
            };
            validateRecord(normalized);
            imported[nodeId] = normalized;
          });
          Object.entries(imported).forEach(([nodeId, record]) => this.store.save(nodeId, record));
          this.render();
          alert(`Imported ${Object.keys(imported).length} coordinate(s).`);
        } catch (error) {
          alert(`Import failed: ${error.message}`);
        }
      };
      reader.readAsText(file);
    }
  }

  global.CoordinateCollectionController = CoordinateCollectionController;
})(window);
