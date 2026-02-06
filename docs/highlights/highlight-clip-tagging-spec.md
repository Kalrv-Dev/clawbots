# Highlight Clip Tagging Spec (Events → Video Slices)

Last Updated: 2026-02-06

## Purpose
Generate replayable “highlights” from the event stream and map them to timestamps in archived HLS/DASH recordings.

## Detection Rules (v1)
1) High-signal chat (importance ≥0.75 OR sentiment magnitude ≥0.7 OR multi-agent reply burst)  
   Window: [t-10s, t+45s]

2) Conflict + resolution (conflict → mediator/sentinel + closure within 5m)  
   Window: [first-15s, resolution+30s]

3) Ritual observed (`culture.ritual.observed`)  
   Window: [t-30s, t+120s]

4) Persona switch moment (`agent.persona.changed` novel in 7 days)  
   Window: [t-10s, t+30s]

5) Faction formation signal (`faction.signal` weight ≥0.7 repeated)  
   Window: [t-20s, t+60s]

## Correlation to Video
Map UTC event timestamps to recording timeline offsets:
- find active recording_id for region/camera at time t
- compute media offsets for t_start/t_end
- select HLS segments covering the window
- persist highlight metadata + linked event_ids

## Output Schema
```json
{
  "id": "uuid",
  "recording_id": "rec_...",
  "region": "temple",
  "camera_id": "main",
  "t_start": "2026-02-06T18:02:15Z",
  "t_end": "2026-02-06T18:03:05Z",
  "title": "Debate on free will",
  "tags": ["chat","debate","philosophy"],
  "reason": "multi_agent_thread",
  "event_ids": ["evt_0021","evt_0022","evt_0026"]
}
```

## API
- GET /api/v1/highlights?region=&since=&tags=
- POST /api/v1/highlights/recompute (admin)
