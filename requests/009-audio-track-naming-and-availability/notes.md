# Implementation notes

Implementation has started on branch `request/009-audio-track-naming-and-availability`.

The Spotify evidence for episode 128 is user supplied: album ID `4TdiUT6sWWBMF4nlwGOiC6`. The user reports that the resource is unavailable and tracks are greyed out. This does not establish the YouTube Music status.

The new chapter convention is not assumed globally by episode number. The parser recognises the marker used in each actual provider tracklist, and chapter counts are derived independently from that provider's numbered tracks.

Actual implementation details and test results will be recorded as work progresses.
