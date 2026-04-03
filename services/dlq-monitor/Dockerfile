# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM ubuntu:22.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Download single-header libraries (no extra build system needed)
RUN wget -q -O httplib.h \
        https://raw.githubusercontent.com/yhirose/cpp-httplib/v0.18.0/httplib.h \
    && wget -q -O json.hpp \
        https://raw.githubusercontent.com/nlohmann/json/v3.11.3/single_include/nlohmann/json.hpp

COPY main.cpp .

RUN g++ -O2 -std=c++17 -o dlq-monitor main.cpp -lpthread

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dlq-monitor /usr/local/bin/dlq-monitor

EXPOSE 5014

CMD ["dlq-monitor"]
