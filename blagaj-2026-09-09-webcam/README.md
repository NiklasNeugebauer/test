# Blagaj public webcam stills — 9 September 2026

Archive stills from a public tourist webcam at Blagaj, Bosnia and Herzegovina,
covering the morning of 9 September 2026.

## The camera

A pan/tilt/zoom (PTZ) webcam operated by **BH Telecom**, branded "Blagaj — moj
radio" (upper left) and "moja tv" (upper right), with a MojaTV weather and
promotional ticker along the bottom. Syndicated through Windy as webcam
**ID 1650525342**, roughly 1.2 km from Blagaj centre.

Live still: `https://images-webcams.windy.com/42/1650525342/current/full/1650525342.jpg`
Player: `https://webcams.windy.com/webcams/public/embed/player/1650525342/day`

It cycles between preset views: a close framing of the Blagaj Tekija and the
cave mouth at the Buna spring; a wide view of the cliff and canyon; a wide view
of the village and valley; a view up the Buna canyon to the eastern ridge; and
— **importantly — a wide view that includes the Stjepan Grad fortress on the
ridge crest.**

The fortress preset is rare. Across the full 24-hour archive it appears in
exactly **two** frames: **06:46:05** and **07:57:07**. It does not recur through
the afternoon.

## Frames

Local time (CEST). `_full` and `_normal` are two resolutions of the same
capture; all 1920x1080.

| File timestamp | Clock in frame | View |
|---|---|---|
| 04:03:09 – 05:45:06 | — | pre-dawn (10-min chain: 04:03, 04:13, 04:23, 04:33, 04:43, 04:53, 05:03, 05:13, 05:24, 05:35, 05:45) |
| 05:55:17 | 05:54 | first light, village lamps still on |
| 06:05:17 | 06:04 | wide, cliff and canyon |
| 06:15:33 | 06:14 | up the canyon, eastern ridge sunlit |
| 06:25:33 | 06:24 | Tekija, spring, bridges |
| 06:35:35 | 06:34 | Tekija + cave mouth, early light, no people |
| **06:46:05** | **06:45** | **wide — the fortress on the ridge crest, in blue pre-sunrise shadow. Closest fortress view to 07:00 (13 min 55 s before).** |
| **06:56:14** | **06:55** | **wide — cliff face catching first sun. Closest frame of any kind to 07:00 (3 min 46 s before).** |
| **07:06:34** | **07:05** | **Tekija, spring, bridges and village (6 min 34 s after 07:00).** |
| 07:16:44 | 07:15 | wide — village and valley, tekke small at centre |
| 07:26:44 | 07:25 | wide up the canyon, sun cresting the eastern ridge |
| 07:36:45 | 07:35 | Tekija, spring and village, first sun on the valley |
| 07:46:47 | 07:45 | Tekija close — cave mouth, bridge, terraces |
| **07:57:07** | **07:56** | **wide — the fortress again, now in full daylight. The clearest view of Stjepan Grad in the set.** |
| 08:07:07 | 08:06 | wide, hillside and cliff |
| 08:17:07 – 10:47:29 | — | daylight (10-min chain: 08:17, 08:27, 08:37, 08:47, 08:57, 09:07, 09:17, 09:27, 09:37, 09:47, 09:57, 10:07, 10:17, 10:27, 10:37, 10:47) |
| `daylight-best-of-day` | 10:46 | Tekija + cave, tourists visible (same capture as 10:47:29) |

The record is **continuous at ~10-minute spacing from 04:03:09 to 10:47:29**.

Derived file:

| File | Description |
|---|---|
| `blagaj_2026-09-09_064605_CEST_fortress-crop.jpg` | The fortress from the 06:46 frame — cropped, upscaled 5x, mild contrast and unsharp mask. Shows the keep at left, the crenellated wall run, and the tall tower fragment. |
| `blagaj_2026-09-09_075707_CEST_fortress-crop.jpg` | The fortress from the 07:57 frame — same ridge, same structures, in daylight. Clearer than the 06:46 crop: the flat-topped bastion, the level curtain wall and the square keep all read as masonry rather than karst. This is the frame that confirms the identification. |

## Why these were collected

The subject event — an engagement at Stjepan Grad (Blagaj Castle), the hilltop
fortress above the village — took place at approximately 07:00 on 9 September
2026. No personal photographs were taken.

## What these do and do not show

**The fortress does appear**, in the 06:46 frame, silhouetted on the ridge crest
about fifteen minutes before the event. That corrects an earlier note in this
file which said the fortress appeared in no preset.

**The people do not.** At roughly 1.2 km, in a wide preset, the whole fortress
spans only about 400 x 70 pixels of a 1920x1080 frame. Two people there would be
far below a single pixel. Nothing in this set shows the couple, and no amount of
enlargement will change that — the information is not in the file.

What this set is: timestamped photographs of the place, on that morning, at that
hour, including the fortress itself in the light they were standing in.

## The archive URL scheme

The frames come from Windy's image proxy, keyed by **Unix timestamp of the
capture**:

```
https://imgproxy.windy.com/_/{size}/plain/day/1650525342/original/{unix_ts}.jpg
```

`{size}` is `full` (1920x1080), `normal` (960x540), `preview` or `thumbnail`.
`original` is accepted and is byte-identical to `full`, so **1920x1080 is the
maximum resolution available** — there is no higher-resolution original to ask
for. `day` can also be `month` (one frame per day) or `year` (roughly one per
week), each with its own key set.

Lookups are exact: an unstored timestamp returns `404 Source is unreachable`,
and neighbouring seconds do not resolve. Two cautions for anyone repeating this:
`curl -X HEAD` returns a **false 200 for every timestamp** because the CDN
answers HEAD without consulting the origin, so probe with real GETs; and the
timestamps drift by 0–30 s per step, so walk the chain (probe t+585..t+655 from
each known frame) rather than assuming a fixed interval.

## Other limitations

- **Archive sampling is ~10 minutes across the whole 24-hour window** — not the
  ~50 minutes an earlier note recorded. 50 minutes is only what Windy's player
  *lists*: it shows 24 evenly spread frames and hides the four intermediate
  captures between each. The underlying store holds every ~10-minute poll, and
  those hidden frames are retrievable by direct URL (see below). Every second
  between 06:35:35 and 07:26:44 was probed individually, so the 10-minute
  spacing in that span is confirmed exhaustively, not assumed.
- **There is no frame at exactly 07:00, and none can exist.** The nearest are
  06:56:14 and 07:06:34.
- The Windy archive is a **rolling 24-hour window**. These frames were retrieved
  on 9 September and would otherwise have been overwritten the following
  morning. Windy's 30-day archive keeps only one midday frame per day, and its
  12-month archive roughly one per week, so no other public source retains the
  07:00-adjacent frames.
- **BH Telecom's own recording runs at full frame rate.** Their live-camera team
  is at `webcam.banner@bhtelecom.ba` (support `podrska@bhtelecom.ba`, contact
  centre 1444). Worth asking for the archive for 06:45–07:15 on 09.09.2026, and
  whether any preset faced Stjepan Grad in that window. Operator retention is
  typically 7–30 days.
- The camera's mounting point is not established. It sits across the valley from
  the cliff, not on the fortress hill.

## Other sources checked, and ruled out

Searched for a mirror sampling the same BH Telecom feed on a different schedule,
which could have held a 07:00 frame. None exists.

- **Carries the camera but re-serves Windy's own images**, so no independent
  cadence or archive: see.cam (`/ba/01/local-community-rodoc-i/local-community-rodoc-i-blagaj`,
  listed as "Local community Rodoč I: Blagaj"; its `youtube_stream_url` is null,
  so there is no stream recording either).
- **Does not carry the camera at all:** SkylineWebcams, whatsupcams, worldcams.tv,
  webcamtaxi, webcamgalore, wetter.com, meteoblue, balticlivecam, elivewebcams,
  worldcam.eu, uzivokamere, bergfex, Ventusky. foxlivecam has a
  `/blagaj-bih-livecam.php` page, but it is a link farm with no embed.
- **No BH Telecom page of its own:** `bhtelecom.ba/webtv.html` now 301s to
  `mojawebtv.bhtelecom.ba/webtv.html`, which returns 404. No public operator-side
  archive or timelapse was found.
- Of the **79 Windy-syndicated cameras in Bosnia and Herzegovina**, this is the
  only one at Blagaj. The rest in the region are petrol-station forecourt,
  border-crossing and roadside cameras (Mostar BP HIFA, Avenija Kralja Tomislava,
  Čapljina, Šurmanci, Humac, Ljubuški, Neum) — all at ground level, all 20 km or
  more away, none with a Blagaj sightline.
- **No other public camera sees the fortress.** BIHAMK and AMS BiH traffic
  cameras cover border crossings, Makljen, Sarajevo and Tuzla — nothing in the
  Mostar basin. There is no webcam at Fortica Sky Park, and the Blagaj
  establishments at the spring (Restoran Vrelo, Tekija Blagaj) have social media
  but no live feed.
- The **HNŽ canton wildfire watch network** — 18 PTZ cameras, including sites at
  Mostar (Fortica) and Stolac (Hrgud) that may have distant sightlines — is run
  from the Civil Protection operational centre in Mostar
  (`upravaczvhnz-k.ba`). It has **no public feed or archive**; any request would
  have to go to the canton directly.

## Light that morning

Sunrise at Blagaj (43.2564 N, 17.8886 E) on 9 September 2026 was **06:21**, with
civil dawn 05:52. But the 06:56 and 07:26 frames show direct sun only reaching
the upper cliff and cresting the eastern ridge — so **the valley floor stayed in
shadow until roughly 07:20–07:30**, an hour after nominal sunrise.

The fortress, at 310 m, catches first light around 06:25–06:35. At 07:00 it was
lit while the whole valley beneath it was still blue. The 06:46 and 06:56 frames
show exactly that division.

**9 September 2027 has an identical 06:21 sunrise.**
