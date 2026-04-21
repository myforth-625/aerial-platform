# Mini Air Simulation (Minimal)

This folder contains a minimal front-end + back-end architecture focused on 3D algorithm visualization.

## Structure

- backend: Spring Boot REST API (in-memory data, no database)
- frontend: React + Vite UI with Three.js 3D playback

## Run Backend

```bash
cd backend
mvn spring-boot:run
```

The API runs on http://localhost:8084 by default.

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI runs on http://localhost:5173 and calls the backend at http://localhost:8084/api.

To change the API base URL, set:

```
VITE_API_BASE_URL=http://localhost:8084/api
```

## Notes

- The simulation data is generated in memory.
- Algorithm integration is stubbed with a built-in generator.
- No database is used.111
