# GhostShell License Server

A universal license validation server for GhostShell instances, built with FastAPI and PostgreSQL.

## Features

- **Universal License Key**: Built-in universal license that works for all instances
- **Individual Licenses**: Create and manage individual license keys
- **Machine Binding**: Licenses are bound to specific machine fingerprints
- **Expiration Management**: Set custom expiration dates for licenses
- **Validation Logging**: Track all license validation attempts
- **Admin API**: Manage licenses and view statistics

## Universal License Key

The server includes a universal license key: `GHOST-SHELL-UNIVERSAL-2024`

This key will work for any GhostShell instance without requiring individual license creation.

## API Endpoints

### Public Endpoints

- `POST /validate` - Validate a license key
- `GET /health` - Health check endpoint

### Admin Endpoints (require JWT token)

- `POST /create` - Create a new license
- `GET /stats` - Get license statistics

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret key for JWT token generation
- `UNIVERSAL_LICENSE_KEY` - The universal license key (default: GHOST-SHELL-UNIVERSAL-2024)
- `PORT` - Server port (default: 8000)

## Deployment on Render

1. **Create PostgreSQL Database**:
   - Go to Render Dashboard
   - Click "New" → "PostgreSQL"
   - Name: `ghostshell-licenses-db`
   - Note the connection details

2. **Deploy Web Service**:
   - Click "New" → "Web Service"
   - Connect your Git repository
   - Use the following settings:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `python main.py`
     - Environment Variables:
       - `DATABASE_URL`: Use the PostgreSQL connection string
       - `JWT_SECRET`: Generate a secure random string
       - `UNIVERSAL_LICENSE_KEY`: `GHOST-SHELL-UNIVERSAL-2024`

3. **Alternative: Use render.yaml**:
   - Include the `render.yaml` file in your repository root
   - Render will automatically configure the database and web service

## Usage Examples

### Validate License (Universal Key)

```bash
curl -X POST "https://black-pessah.onrender.com/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "GHOST-SHELL-UNIVERSAL-2024",
    "fingerprint": {
      "machine_id": "your-machine-id",
      "platform": "linux",
      "arch": "x64"
    },
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "1.0.0"
  }'
```

### Create New License (Admin)

```bash
curl -X POST "https://black-pessah.onrender.com/create" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_SECRET" \
  -d '{
    "expires_in_days": 365,
    "max_instances": 1
  }'

```

### Get Statistics (Admin)

```bash
curl -X GET "https://black-pessah.onrender.com/stats" \
  -H "Authorization: Bearer $env:JWT_SECRET" `
```

## Security Features

- JWT signature verification for license validation requests
- Machine fingerprint binding to prevent license sharing
- Admin endpoints protected with bearer token authentication
- Comprehensive validation logging for audit trails
- Rate limiting and request validation

## Database Schema

The server automatically creates the following tables:

- `licenses` - Store license keys, expiration, and machine bindings
- `validation_logs` - Log all validation attempts for auditing

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables in `.env` file

3. Start the server:
   ```bash
   python main.py
   ```

4. Access the API documentation at `http://localhost:8000/docs`