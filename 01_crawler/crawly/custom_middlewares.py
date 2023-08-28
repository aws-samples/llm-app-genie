from time import sleep

import crawly.settings as settings
from scrapy.downloadermiddlewares.retry import RetryMiddleware, get_retry_request


class CustomRetryMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if response.status in settings.RETRY_HTTP_CODES:
            # Check if the request has met the maximum retry times.
            if self._retry_times_exceeded(request):
                return response  # don't retry anymore

            # Add a custom delay (e.g., 5 seconds) between retries.
            sleep(settings.RETRY_DELAY)

            # Use the _retry method to get a new request for retry
            new_request = self._retry(
                request=request,
                reason=f"Retry on status {response.status}",
                spider=spider,
            )

            if new_request:
                new_request.priority = request.priority + self.priority_adjust
                return new_request

        return response  # return the original response if no retry needed

    def _retry_times_exceeded(self, request):
        # Check if the request has met or exceeded the maximum retry times.
        retry_times = request.meta.get("retry_times", 0)

        return retry_times >= self.max_retry_times
