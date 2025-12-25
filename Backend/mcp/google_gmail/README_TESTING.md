# Gmail MCP Server Testing Guide

## Automated Tests

Run the automated test suite:

```bash
cd Backend/mcp/google_gmail
python test_gmail.py
```

### What the tests cover:
- ✅ Token storage (save/retrieve/update/delete)
- ✅ Token expiry logic
- ✅ Non-existent token handling
- ✅ Default user configuration check

## Manual Testing

### 1. Start the Server

```bash
python -m Backend.mcp.google_gmail.server
```

Server will run on `http://localhost:3031`

### 2. Test Authentication Flow

#### Generate Auth URL
```python
# Tool: gmail_generate_auth_url
# No parameters needed (uses DEFAULT_USER_EMAIL)
```

Expected response:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "authenticated": false
}
```

Or if already authenticated:
```json
{
  "message": "Already authenticated for mahdiharoun44@gmail.com",
  "authenticated": true
}
```

#### Complete OAuth Flow
1. Visit the auth_url in browser
2. Grant permissions
3. You'll be redirected to callback
4. Tokens are automatically saved to database

#### Check Auth Status
```python
# Tool: check_gmail_auth_status
# No parameters needed
```

Expected response:
```json
{
  "authenticated": true,
  "email": "mahdiharoun44@gmail.com"
}
```

### 3. Test Email Operations

#### List Emails
```python
# Tool: list_gmail_messages
{
  "max_results": 10,
  "query": "is:unread"
}
```

#### Get Email Details
```python
# Tool: get_gmail_message
{
  "message_id": "abc123xyz"
}
```

#### Send Email
```python
# Tool: send_gmail_message
{
  "to": "recipient@example.com",
  "subject": "Test Email",
  "body": "This is a test message"
}
```

#### Send Email with S3 Attachment
```python
# Tool: send_gmail_message_with_s3_attachment
{
  "to": "recipient@example.com",
  "subject": "Test with Attachment",
  "body": "See attached file",
  "attachment_s3_key": "path/to/file.pdf"
}
```

### 4. Test Token Persistence

1. Send an email (tokens are used)
2. Stop the server
3. Restart the server
4. Send another email (should work without re-authentication)
5. Tokens should automatically refresh when expired

### 5. Test Token Revocation

```python
# Tool: revoke_gmail_access
# No parameters needed
```

Expected response:
```json
{
  "success": true,
  "message": "Access revoked for mahdiharoun44@gmail.com"
}
```

After revocation, email operations should fail until re-authentication.

## Database Verification

Check tokens in PostgreSQL:

```sql
-- View stored tokens
SELECT email, expires_at, created_at, updated_at 
FROM gmail_tokens;

-- Check if token is expired
SELECT email, 
       expires_at < NOW() as is_expired,
       expires_at - NOW() as time_remaining
FROM gmail_tokens;
```

## Troubleshooting

### Issue: "User not authenticated"
- Run `gmail_generate_auth_url`
- Complete OAuth flow in browser

### Issue: "Token expired"
- Tokens should auto-refresh
- If refresh fails, re-authenticate
- Check `refresh_token` exists in database

### Issue: "Database connection failed"
- Verify PostgreSQL is running
- Check .env file has correct DB credentials:
  - `DB_HOST`
  - `DB_PORT` 
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`

### Issue: "invalid_grant error"
- Refresh token was revoked
- Re-authenticate to get new tokens

## Expected Token Behavior

| Scenario | Expected Behavior |
|----------|-------------------|
| First use | Requires authentication |
| Token valid (>5 min remaining) | Used directly |
| Token expiring soon (<5 min) | Auto-refreshed |
| Token expired | Auto-refreshed |
| Refresh token invalid | Requires re-authentication |
| Server restart | Tokens persist, no re-auth needed |
| Token revoked by user | Cleared from DB, requires re-auth |

## Success Criteria

✅ All automated tests pass  
✅ OAuth flow completes successfully  
✅ Emails can be sent and received  
✅ Tokens persist across server restarts  
✅ Tokens auto-refresh when expired  
✅ Multi-user support works (if testing with multiple emails)  
✅ Token revocation clears data  
