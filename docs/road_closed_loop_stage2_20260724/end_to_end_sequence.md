# Closed-loop sequence

```mermaid
sequenceDiagram
    participant Sensor as Road inspection and sensors
    participant A1 as Agent1 observation operator
    participant State as Frozen analysis-state registry
    participant A3 as RoadClosedLoopForecaster
    participant A2 as Agent2 trigger policy
    participant Risk as Scenario hazard/RUL head

    Sensor->>A1: y_n, mask, registration, traffic/environment, provenance
    A1->>State: road_assimilated_state_v1 + SHA-256
    State->>A3: z_analysis, uncertainty semantics, graph, origin/mask hash
    A3->>A3: Direct h1-h3 field forecast
    A3->>A2: Model uncertainty, innovation, OOD, data quality, maintenance
    A2-->>A3: continue / request / stop_and_request
    alt continue
        A3-->>Sensor: h1-h3 fields with evidence status
        A3->>Risk: Future traffic, environment and maintenance scenarios
        alt risk heads trained and calibrated
            Risk-->>Sensor: Hazard, threshold probability and RUL distribution
        else risk heads untrained
            Risk-->>Sensor: unavailable_untrained
        end
    else request or stop
        A3-->>Sensor: Inspection request; withhold recursive field forecast
        Sensor->>A1: New observation
        A1->>State: New frozen analysis state and hashes
        State->>A3: Re-assimilate and reset trigger history
    end
```

The current c87 execution is a synthetic FEM-oracle compatibility smoke. It
does not contain real road observations, calibrated uncertainty, or trained
risk heads.
