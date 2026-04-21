# Texas Hold'em Poker Analyzer — Architecture Overview

## Project Structure

```
poker_analyzer/
├── ARCHITECTURE.md          # This file
├── requirements.txt         # Dependencies
├── config/
│   └── regions.json         # Bounding box config per resolution
├── module1_vision/
│   ├── __init__.py
│   ├── parser.py            # Main image parsing orchestrator
│   ├── preprocessor.py      # Image normalization & enhancement
│   ├── card_detector.py     # Hole card & community card detection
│   ├── ocr_reader.py        # Stack/pot size OCR
│   └── position_detector.py # Dealer button detection
├── module2_engine/          # (Phase 3)
│   ├── __init__.py
│   ├── equity.py            # treys integration
│   ├── gto_charts.py        # Pre-flop chart loader
│   └── decision.py          # Action recommender
├── module3_ui/              # (Phase 4)
│   ├── __init__.py
│   └── app.py               # Streamlit UI
├── data/
│   └── gto_charts/          # CSV files per position/stack depth
└── tests/
    ├── test_vision.py
    └── sample_screenshots/
```

## Data Flow

```
Screenshot (PNG/JPG)
        │
        ▼
[Preprocessor]
  - Resize to canonical resolution (1920×1080 baseline)
  - Denoise, sharpen
  - Contrast normalization
        │
        ▼
[Card Detector]               [OCR Reader]              [Position Detector]
  - Template matching          - Region crop              - Dealer button
  - Suit/rank classification   - Binarize text            - Seat numbering
  - Hole cards + community     - pytesseract / easyocr
        │                             │                          │
        └──────────────────┬──────────┘──────────────────────────┘
                           ▼
                    [GameState dict]
          {
            hole_cards: ["Ah", "Kd"],
            community: ["2c", "7h", "Js"],
            pot: 1250,
            my_stack: 8450,
            villain_stack: 6200,
            position: "BTN",
            street: "flop"
          }
                           │
                           ▼
                   [Module 2 Engine]  →  [Module 3 UI]
```

## Key Design Decisions

1. **Resolution normalisation first** — all downstream logic operates on a
   canonical 1920×1080 frame. Bounding boxes are defined once at that resolution.

2. **Dual OCR strategy** — easyOCR for coloured/styled text (stacks),
   pytesseract with binarization for clean white-on-dark text (pot).

3. **Bounding box config externalised** — `config/regions.json` lets you
   override any region without touching code.

4. **Fail-safe returns** — every detector returns None on failure rather than
   crashing, so partial results still flow to the engine.
