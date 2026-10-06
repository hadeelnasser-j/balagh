from app.routers import dubbing, health, jobs, projects, segments, sources, subtitles

ALL_ROUTERS = [health.router, projects.router, segments.router, sources.router, subtitles.router,
               dubbing.router, jobs.router]
