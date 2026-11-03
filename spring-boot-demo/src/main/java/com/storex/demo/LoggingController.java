package com.storex.demo;

import java.time.Instant;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class LoggingController {

    private static final Logger LOGGER = LoggerFactory.getLogger(LoggingController.class);
    private static final int MAX_LOG_COUNT = 20_000;

    @GetMapping("/test-log")
    public ResponseEntity<LogResponse> testLog() {
        String eventId = UUID.randomUUID().toString();
        LOGGER.info("Test INFO event event_id={} timestamp={}", eventId, Instant.now());
        LOGGER.warn("Test WARN event event_id={} timestamp={}", eventId, Instant.now());
        LOGGER.error("Test ERROR event event_id={} timestamp={}", eventId, Instant.now());
        return ResponseEntity.ok(new LogResponse("Logged INFO, WARN, and ERROR", 3, eventId));
    }

    @GetMapping("/generate-logs")
    public ResponseEntity<LogResponse> generateLogs(
            @RequestParam(defaultValue = "10000") int count
    ) {
        if (count < 1 || count > MAX_LOG_COUNT) {
            return ResponseEntity.badRequest()
                    .body(new LogResponse("count must be between 1 and " + MAX_LOG_COUNT, count, null));
        }

        String eventId = UUID.randomUUID().toString();
        for (int i = 0; i < count; i++) {
            String message = "Generated load-test log event";
            Instant timestamp = Instant.now();
            switch (i % 3) {
                case 0 -> LOGGER.info("{} event_id={} sequence={} timestamp={}", message, eventId, i, timestamp);
                case 1 -> LOGGER.warn("{} event_id={} sequence={} timestamp={}", message, eventId, i, timestamp);
                default -> LOGGER.error("{} event_id={} sequence={} timestamp={}", message, eventId, i, timestamp);
            }
        }
        return ResponseEntity.ok(new LogResponse("Generated log events", count, eventId));
    }

    public record LogResponse(String message, int count, String eventId) {
    }
}
