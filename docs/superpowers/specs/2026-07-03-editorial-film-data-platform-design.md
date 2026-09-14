# Editorial Film Data Platform Design

## Project

Turn the existing Dapuqiao scenario metrics and regime outputs into a cinematic data-visualization platform and a 10-second exhibition-style short sequence.

This is not a dashboard. It is a narrative data surface where metrics appear as evidence inside a spatial story.

## Goal

Build a visual language that lets viewers feel the difference between scenarios without reading a dense analytics interface.

The deliverable has two connected forms:

1. A browser-based interactive platform with film-like layout and restrained data overlays.
2. A 10-second scripted sequence that can be exported as video.

## Design Position

The chosen direction is `Editorial Film`.

That means:

- Spatial atmosphere stays primary.
- Data is secondary but sharp.
- Metrics appear in timed moments rather than filling the whole screen.
- The interface should feel like a gallery film frame, not a control room.

## Experience Principles

### 1. Data appears only when it has narrative value

Each beat should reveal one or two key changes, not a full report.

### 2. Motion should communicate transformation, not decoration

Every animated element must correspond to a scenario change, operator effect, or metric shift.

### 3. The viewer should understand direction before precision

The audience should first feel:

- more intense
- more open
- more fragmented
- more negotiated

Exact values support this reading but do not dominate it.

### 4. Keep one visual language across map, massing, and metrics

The platform should look like one coherent film surface rather than separate modules glued together.

## Platform Structure

### Main composition

- Center: massing or map-based scenario image layer
- Left: short narrative caption and minimal key figures
- Right: scenario stack, one card per regime
- Bottom: thin timeline and operator capsules

### Interaction model

- Default mode behaves like a looping short film
- Clicking a scenario card isolates that scenario and plays its transformation sequence
- Data overlays stay lightweight unless interaction triggers a closer reading

## Visual Language

Use only four families of data marks.

### 1. Number subtitles

Purpose:
- baseline metrics
- scene headers
- key before/after values

Style:
- large numeric type
- small uppercase labels
- cinematic spacing

### 2. Thin bands

Purpose:
- flow pressure
- frontage share
- access intensity

Style:
- horizontal or slightly curved strips
- subtle glow
- transform through stretch, contraction, or color drift

### 3. Arc or halo marks

Purpose:
- stakeholder share
- protected share
- coverage change

Style:
- restrained radial indicators
- never full dashboard donuts

### 4. Particle split or micro-unit fields

Purpose:
- micro-lease emergence
- fragmentation
- fine-grain intensification

Style:
- small distributed units
- should feel spatial, not statistical

## Metrics To Use

### Tier 1: already available and highly usable

- building count
- average height
- max height
- slenderness
- scenario building count after operator chain
- stakeholder counts
- relief nodes
- one-way alleys
- quiet buildings

### Tier 2: desirable if available from 05-side measures

- ground coverage ratio
- mean footprint area
- fragmentation or subdivision intensity
- protected frontage share

The first implementation should work with Tier 1 only. Tier 2 can be added if extraction is straightforward.

## Scenario Signatures

Each scenario should have one dominant data identity.

### Tourism Capture

Visual signal:
- hotter accent
- stronger frontage bands
- increased slender massing

Key metrics:
- commercial or development dominance
- increased slenderness
- increased final building count after splitting

### Everyday Life First

Visual signal:
- cooler accent
- more open ground feel
- reduced pressure bands

Key metrics:
- lower intensity
- more released ground
- calmer access field

### Heritage Micro-Economy

Visual signal:
- fine-grain particle spread
- heritage halo
- low-rise continuity

Key metrics:
- micro-lease emergence
- distributed small units
- preservation over consolidation

### Negotiated 24h Alley

Visual signal:
- mixed warm/cool temporal band
- relief node pulses
- quiet zone dimming

Key metrics:
- relief nodes
- one-way alleys
- quiet-mode buildings

## 10-Second Film Script

### Beat 1: 0.0s to 2.0s

Title: `Baseline`

Frame:
- dark map or massing field
- one-line narrative opener
- three baseline numbers count in

Content:
- building count
- average height
- stakeholder groups

Purpose:
- establish that one district can be rewritten in multiple ways

### Beat 2: 2.0s to 4.5s

Title: `Pressure Shift`

Frame:
- transition from Tourism Capture to Everyday Life First

Content:
- a thin pressure band intensifies, then relaxes
- a radial or strip metric shifts from extraction to release

Purpose:
- show that scenario change is spatial and political, not only formal

### Beat 3: 4.5s to 7.5s

Title: `Fine-Grain Survival`

Frame:
- Heritage Micro-Economy

Content:
- larger mass breaks into smaller particles or field units
- heritage protection appears as a thin gold trace

Purpose:
- make fragmentation feel intentional and productive rather than chaotic

### Beat 4: 7.5s to 10.0s

Title: `Timed Negotiation`

Frame:
- Negotiated 24h Alley

Content:
- warm-to-cool time band
- relief node pulses
- quiet buildings dim or outline

Purpose:
- end on the idea that space is scheduled and negotiated, not fixed

## Interface Behavior

### Default loop

The platform loops like a short film:

- baseline
- operator activation
- scenario comparisons
- negotiated final state

### Scenario click

When a user clicks a scenario card:

- the main view isolates that scenario
- the operator chain plays in sequence
- the bottom capsules highlight one by one
- the data overlay updates to that scenario's signature marks

## Motion Rules

- Use easing that feels editorial and deliberate, not bouncy
- Prefer fades, drifts, tracing, and pulsing
- Avoid large-scale spinning charts or aggressive dashboard transitions
- Data motion should always be slower than hard UI motion and slightly behind massing changes

## Content Rules

- No dense table blocks in the main short-film mode
- No more than two active metric statements per beat
- Labels should be short and legible in motion
- Use English on-screen copy if the output is intended for the current film export set

## Implementation Strategy

### Phase 1

Create a new browser-based page that reuses:

- current intro story geometry payload
- scenario sequence geometry
- regime metadata
- available scenario metrics

Deliver:
- a 10-second editorial data loop
- exportable video frames

### Phase 2

Expand the page into an interactive platform:

- scenario inspection
- alternate metric overlays
- optional slower comparison mode

### Phase 3

If needed, add richer 05-side metrics and secondary scenes.

## Technical Notes

- Reuse the existing `intro_story` data pipeline where possible.
- Keep the exported frame path deterministic for video generation.
- The 10-second sequence should render from a single-page source so browser capture remains stable.
- Prefer lightweight SVG, HTML, and canvas overlays over heavy charting libraries.

## Risks

### Risk 1: too much information

If too many metrics are visible at once, the work collapses back into dashboard language.

Mitigation:
- enforce one to two core metric moments per beat

### Risk 2: data looks disconnected from massing

If overlays do not move with scenario changes, the film feels fake.

Mitigation:
- tie every overlay change to a regime or operator state change

### Risk 3: over-stylized but unreadable

If atmosphere becomes too dominant, the audience misses the evidence.

Mitigation:
- preserve strong contrast and short labels

## Recommendation

Build the short-film version first, not the full interactive system.

Success for the first pass means:

- it looks cinematic
- scenario differences are legible within 10 seconds
- data overlays feel integrated with spatial change
- the result is exportable as video without manual compositing

## Next Step

After approval, write the implementation plan for:

1. data extraction and metric packing
2. editorial film page structure
3. timed overlay animation system
4. 10-second export pipeline
