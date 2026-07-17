# R3VP API Reference

`openapi.json` is the OpenAPI 3.1 specification for the R3VP API, exported
directly from the running FastAPI application (115 operations across 99
paths).

## View it

- **Hosted**: https://omarrao.github.io/r3vp/api-spec/ (rendered with Redoc)
- **Live, from a running API**: Swagger UI at `http://localhost:8000/docs`,
  ReDoc at `http://localhost:8000/redoc`

## Use it in a client

`openapi.json` imports directly into API clients:

- **Postman**: Import > File > select `openapi.json` (generates a request
  collection with every endpoint)
- **Insomnia**: Import from File > `openapi.json`
- **Code generation**: `openapi-generator-cli generate -i openapi.json -g <lang>`

## Regenerate

The spec is checked in so it renders on GitHub Pages without a running
backend. Regenerate it after changing routes or schemas:

```bash
cd apps/api
uv run python -c "import json; from src.main import app; \
  open('../../docs/api-spec/openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
```

## Authentication

All endpoints require a bearer token (Auth0 JWT) unless noted. Send
`Authorization: Bearer <token>`; the token's roles map to the RBAC
permissions documented per operation.
