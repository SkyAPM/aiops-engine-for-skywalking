# SkyWalking AIOps Engine
**An AIOps Engine for Observability.**

A usable open-source AIOps framework for the domain of cloud computing observability. 

### Why this project matters?
We could answer this from the following progressive questions:
1. Are there existing algorithms for telemetry data? 
   - **Abundant.**

2. Are the existing algorithms empirically verified? 
   
   - **Most proposed algorithms are not empirically verified**

3. Are there AIOps tools that embed machine learning algorithms? 
   - **Limited, often out of maintenance or commercialized.**
   
4. Are there open-source AIOps solutions that integrates with popular backends?
   - **Hardly any.**

5. Why would I need that?
   1. For developers & organizations curious for AIOps:
      - a. Just install and start using it, saves budget, saves head-scratching.
      - b. Treat this project as a good (or bad) reference for your own AIOps pipeline.
   2. For researchers in the AIOps domain:
      - a. For software engineering researchers - sample for AIOps evolution and empirical study.
      - b. For algorithm researchers - playground for new algorithms, solid case studies.
      

The above is where we place the value of this project, though our current aim is to become the official AIOps engine 
of [Apache SkyWalking](https://github.com/apache/skywalking), each component could be easily swapped given its 
plugable design.

### Current Goal

At the current stage, it serves as an **anomaly detection** engine, in the future, we will also explore root cause analysis and 
automatic problem recovery.

This is also the tentative repository for OSPP 2022 and GSOC 2022 student project outcomes.

Project `Exploration of Advanced Metrics Anomaly Detection & Alerts with Machine Learning in Apache SkyWalking`

Project `Log Outlier Detection in Apache SkyWalking`

### Architecture

**TBA**

**Data pulling:**

The current data pulling and retention rely on a common set of ingestion methods, with a 
first focus on SkyWalking OAP GraphQL and static file loader. We maintain a local storage for processed data.

**Alert component:**

An anomaly does not directly trigger an alert, it 
goes through a tolerance mechanism.

### Roadmap

Phase 0 (current)
1. [ ] Implement essential development infrastructure.
2. [ ] Implement naive algorithms as baseline & pipline POC (on existing datasets).
3. [ ] Implement a SkyWalking `GraphQLDataLoaderProvider` to test data pulling.

Phase 1 (summer -> fall 2022, OSPP & GSOC period)
1. [ ] Implement the remaining core default providers.
2. [ ] **Research and implement algorithms with OSPP & GSOC students.**
3. [ ] Integrate with Apache Airflow for orchestration.
5. [ ] Evaluation based on benchmark microservices systems (anomaly injection).
6. [ ] MVP ready without UI-side changes. 

Phase 2 (fall -> end of 2022)
1. [ ] Join as an Apache SkyWalking subproject.
2. [ ] Integrate with SkyWalking Backend & rule-based alert module.
3. [ ] Propose and request SkyWalking UI-side changes.
4. [ ] First release for end-user testing.

Phase Next 
1.[ ] Towards production-ready.
