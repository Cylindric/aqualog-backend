const SMTPServer = require('smtp-server').SMTPServer;
const simpleParser = require('mailparser').simpleParser;
const axios = require('axios');

// Read configurations from Docker environment variables
const API_KEY = process.env.SMTPFAST_API_KEY;
const API_URL = process.env.SMTPFAST_API_URL || 'https://smtpfa.st/api/v1/email';
const PORT = process.env.PORT || 25;

if (!API_KEY) {
    console.error('Error: SMTPFAST_API_KEY environment variable is missing.');
    process.exit(1);
}

const server = new SMTPServer({
    authOptional: true, // Allow local applications to relay without auth
    disabledCommands: ['AUTH'], // Disable explicit auth to make it easy for local apps
    onData(stream, session, callback) {
        simpleParser(stream, {}, async (err, parsed) => {
            if (err) {
                console.error('Parsing error:', err);
                return callback(new Error('Failed to parse raw SMTP payload'));
            }

            // Extract email addresses from structured object arrays
            const fromEmail = parsed.from?.value[0]?.address || session.envelope.mailFrom.address;
            const toEmails = parsed.to?.value.map(t => t.address) || session.envelope.rcptTo.map(r => r.address);

            // Construct the payload matching the SMTPfast JSON specification
            const payload = {
                from: fromEmail,
                to: toEmails,
                subject: parsed.subject || '(No Subject)',
                text: parsed.text || '',
                html: parsed.html || parsed.textAsHtml || ''
            };

            // Safely map CC and BCC fields if present
            if (parsed.cc) payload.cc = parsed.cc.value.map(c => c.address);
            if (parsed.bcc) payload.bcc = parsed.bcc.value.map(b => b.address);

            // Handle file attachments if present (SMTPfast expects base64 or files)
            if (parsed.attachments && parsed.attachments.length > 0) {
                payload.attachments = parsed.attachments.map(att => ({
                    filename: att.filename,
                    content: att.content.toString('base64'),
                    type: att.contentType
                }));
            }

            try {
                // Forward the mail out via an HTTP REST Request
                const response = await axios.post(API_URL, payload, {
                    headers: {
                        'Authorization': `Bearer ${API_KEY}`,
                        'Content-Type': 'application/json'
                    }
                });

                console.log(`Successfully forwarded email to SMTPfast. API Status: ${response.status}`);
                callback(); // Signal to the calling local app that the email was accepted
            } catch (apiError) {
                const errorDetails = apiError.response?.data || apiError.message;
                console.error('SMTPfast API Transmission Failed:', errorDetails);

                // Returning an error tells your local application that delivery failed
                callback(new Error(`Upstream API Error: ${JSON.stringify(errorDetails)}`));
            }
        });
    }
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`SMTP-to-API Gateway running inside container on port ${PORT}`);
    console.log(`Forwarding targets upstream to: ${API_URL}`);
});
