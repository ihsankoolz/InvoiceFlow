/**
 * dlq-monitor — Dead-letter queue depth monitor for InvoiceFlow.
 *
 * Endpoints:
 *   GET /health          — liveness check
 *   GET /api/dlq/status  — list DLQ queues with message counts
 *   GET /api/dlq/queues  — alias for /api/dlq/status
 *   GET /metrics         — minimal Prometheus counters
 *
 * Config (env vars):
 *   RABBITMQ_MGMT_URL    (default: http://rabbitmq:15672)
 *   RABBITMQ_USER        (default: guest)
 *   RABBITMQ_PASS        (default: guest)
 */

#include "httplib.h"
#include "json.hpp"

#include <atomic>
#include <cstdlib>
#include <iostream>
#include <string>

using json = nlohmann::json;

// ── Config ────────────────────────────────────────────────────────────────────

static std::string getenv_or(const char* key, const char* fallback) {
    const char* v = std::getenv(key);
    return v ? v : fallback;
}

// ── Metrics ───────────────────────────────────────────────────────────────────

static std::atomic<uint64_t> g_requests{0};
static std::atomic<uint64_t> g_errors{0};

// ── Main ──────────────────────────────────────────────────────────────────────

int main() {
    const std::string mgmt_url = getenv_or("RABBITMQ_MGMT_URL", "http://rabbitmq:15672");
    const std::string rmq_user = getenv_or("RABBITMQ_USER", "guest");
    const std::string rmq_pass = getenv_or("RABBITMQ_PASS", "guest");

    httplib::Server svr;

    // GET /health
    svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        g_requests++;
        res.set_content(R"({"status":"ok","service":"dlq-monitor"})", "application/json");
    });

    // GET /api/dlq/status  and  GET /api/dlq/queues  (identical behaviour)
    auto dlq_handler = [&](const httplib::Request&, httplib::Response& res) {
        g_requests++;

        httplib::Client cli(mgmt_url);
        cli.set_basic_auth(rmq_user, rmq_pass);
        cli.set_connection_timeout(5);
        cli.set_read_timeout(5);

        auto r = cli.Get("/api/queues");
        if (!r || r->status != 200) {
            g_errors++;
            res.status = 503;
            res.set_content(R"({"detail":"RabbitMQ management API unavailable"})",
                            "application/json");
            return;
        }

        auto all_queues = json::parse(r->body, nullptr, /*allow_exceptions=*/false);
        if (all_queues.is_discarded()) {
            g_errors++;
            res.status = 502;
            res.set_content(R"({"detail":"Invalid JSON from RabbitMQ"})", "application/json");
            return;
        }

        json   dlq_queues = json::array();
        int    total      = 0;

        for (const auto& q : all_queues) {
            if (!q.contains("name")) continue;
            const std::string name = q["name"].get<std::string>();

            // Only queues whose name ends with ".dlq"
            if (name.size() < 4 || name.compare(name.size() - 4, 4, ".dlq") != 0)
                continue;

            int msgs = q.value("messages", 0);
            total += msgs;

            dlq_queues.push_back({
                {"name",                    name},
                {"messages",                msgs},
                {"messages_ready",          q.value("messages_ready", 0)},
                {"messages_unacknowledged", q.value("messages_unacknowledged", 0)},
                {"consumers",               q.value("consumers", 0)},
            });
        }

        if (total > 0) {
            std::cerr << "[dlq-monitor] WARNING: " << total
                      << " unprocessed message(s) across " << dlq_queues.size()
                      << " DLQ queue(s)\n";
        }

        json result = {{"total_dlq_messages", total}, {"queues", dlq_queues}};
        res.set_content(result.dump(), "application/json");
    };

    svr.Get("/api/dlq/status", dlq_handler);
    svr.Get("/api/dlq/queues",  dlq_handler);

    // GET /metrics  — minimal Prometheus exposition
    svr.Get("/metrics", [](const httplib::Request&, httplib::Response& res) {
        std::string m;
        m += "# HELP dlq_monitor_http_requests_total Total HTTP requests handled\n";
        m += "# TYPE dlq_monitor_http_requests_total counter\n";
        m += "dlq_monitor_http_requests_total " + std::to_string(g_requests.load()) + "\n";
        m += "# HELP dlq_monitor_http_errors_total Total error responses returned\n";
        m += "# TYPE dlq_monitor_http_errors_total counter\n";
        m += "dlq_monitor_http_errors_total " + std::to_string(g_errors.load()) + "\n";
        res.set_content(m, "text/plain; version=0.0.4");
    });

    std::cout << "[dlq-monitor] Listening on 0.0.0.0:5014\n";
    svr.listen("0.0.0.0", 5014);
    return 0;
}
