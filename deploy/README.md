# Deployment contract

Run additive database migrations before deploying the API and frontend. Long research runs execute in the persistent worker, never in a short-lived request. Configure provider secrets only in the server environment; browser bundles receive no credentials.

Release order: backup → migrations → worker → API → frontend → health check → golden fixture → scheduler. Roll back application images first; revert a bad watchlist publication to the last known-good period. Never roll back a migration destructively without a tested backup restore.
