package org.ovirt.authentication;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLEncoder;
import java.security.KeyManagementException;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.Calendar;
import java.util.Date;
import java.util.Properties;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;
import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.security.Authentication;
import org.springframework.security.GrantedAuthority;
import org.springframework.security.GrantedAuthorityImpl;
import org.springframework.security.context.SecurityContextHolder;
import org.springframework.security.providers.UsernamePasswordAuthenticationToken;
import org.springframework.security.ui.AuthenticationDetailsSource;
import org.springframework.security.ui.FilterChainOrder;
import org.springframework.security.ui.WebAuthenticationDetailsSource;
import org.springframework.security.ui.preauth.AbstractPreAuthenticatedProcessingFilter;

import com.jaspersoft.jasperserver.api.metadata.user.domain.impl.client.MetadataUserDetails;

/*
 * This class is a pre-authentication filter for the oVirt engine.
 * The purpose is to support using the Reports server from within the oVirt web admin.
 * It gets a session ID, and validates it using the oVirt engine, getting the logged-in user.
 */
public class EngineSimplePreAuthFilter extends AbstractPreAuthenticatedProcessingFilter {
    private final Log logger = LogFactory.getLog(EngineSimplePreAuthFilter.class);

    private final String SESSION_DATA_FORMAT = "sessionID=%1$s";
    private final int DEFAULT_POLLING_TIMEOUT = 60; // in seconds

    private URL getSessionUserGetSessionUserServletURL;
    private int pollingTimeout;
    private String sslTrustStoreType = "JKS";
    private String sslTrustStorePath;
    private String sslTrustStorePassword;
    private String sslProtocol = "TLS";
    private boolean sslInsecure = false;
    private boolean sslNoHostVerification = false;
    private String authenticationProperties;

    protected AuthenticationDetailsSource authenticationDetailsSource = new WebAuthenticationDetailsSource();

    private SSLContext sslctx;

    private void setupSSLContext() throws KeyStoreException, FileNotFoundException, IOException, NoSuchAlgorithmException, KeyManagementException, CertificateException {
        TrustManager[] trustManagers = null;
        if (sslInsecure) {
            trustManagers = new TrustManager[] {
                new X509TrustManager() {
                    @Override
                    public void checkClientTrusted(X509Certificate[] certs, String authType) throws CertificateException {}
                    @Override
                    public void checkServerTrusted(X509Certificate[] certs, String authType) throws CertificateException {}
                    @Override
                    public X509Certificate[] getAcceptedIssuers() {
                        return new X509Certificate[] {};
                    }
                }
            };
        } else {
            if (sslTrustStorePath != null && sslTrustStorePassword != null) {
                try(InputStream in = new FileInputStream(sslTrustStorePath)) {
                    KeyStore trustStore = KeyStore.getInstance(sslTrustStoreType);
                    trustStore.load(in, sslTrustStorePassword.toCharArray());
                    TrustManagerFactory trustManagerFactory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
                    trustManagerFactory.init(trustStore);
                    trustManagers = trustManagerFactory.getTrustManagers();
                }
            }
        }

        sslctx = SSLContext.getInstance(sslProtocol);
        sslctx.init(null, trustManagers, null);
    }

    @Override
    public void afterPropertiesSet() throws Exception {
        super.afterPropertiesSet();

        if (authenticationProperties != null) {
            File authenticationPropertiesFile = new File(authenticationProperties);
            if (!authenticationPropertiesFile.exists()) {
                logger.warn(String.format("authenticationProperties '%s' cannot be found", authenticationProperties));
            }
            else {
                try(InputStream in = new FileInputStream(authenticationPropertiesFile)) {
                    Properties props = new Properties();
                    props.load(in);
                    getSessionUserGetSessionUserServletURL = new URL(props.getProperty("getSessionUserGetSessionUserServletURL", String.valueOf(getSessionUserGetSessionUserServletURL)));
                    pollingTimeout = Integer.valueOf(props.getProperty("pollingTimeout", Integer.toString(pollingTimeout)));
                    sslTrustStoreType = props.getProperty("sslTrustStoreType", sslTrustStoreType);
                    sslTrustStorePath = props.getProperty("sslTrustStorePath", sslTrustStorePath);
                    sslTrustStorePassword = props.getProperty("sslTrustStorePassword", sslTrustStorePassword);
                    sslProtocol = props.getProperty("sslProtocol", sslProtocol);
                    sslInsecure = Boolean.valueOf(props.getProperty("sslInsecure", Boolean.toString(sslInsecure)));
                    sslNoHostVerification = Boolean.valueOf(props.getProperty("sslNoHostVerification", Boolean.toString(sslNoHostVerification)));
                }
            }
        }

        setupSSLContext();
    }

    @Override
    protected Object getPreAuthenticatedCredentials(HttpServletRequest arg0) {
        return null;
    }

    @Override
    protected Object getPreAuthenticatedPrincipal(HttpServletRequest arg0) {
        return null;
    }

    @Override
    public int getOrder() {
        return FilterChainOrder.PRE_AUTH_FILTER;
    }

    @Override
    public void doFilterHttp(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws IOException, ServletException {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || (authentication != null && !authentication.isAuthenticated())) {
            logger.debug("authentication context is either null, or not authenticated. Validating session.");
            SecurityContextHolder.getContext().setAuthentication(getAuthRequest(request));
        } else {
            // The logic here is that if we are already authenticated, and the authentication was done in this pre-auth filter, then we check if we need
            // to re-check our token
            Object principal = authentication.getPrincipal();
            if (principal instanceof MetadataUserDetails) {
                MetadataUserDetails metadataUserDetails = (MetadataUserDetails) principal;
                UsernamePasswordAuthenticationToken originalAuthentication = (UsernamePasswordAuthenticationToken) metadataUserDetails.getOriginalAuthentication();

                if (originalAuthentication != null && originalAuthentication.getPrincipal() instanceof EngineUserDetails) {
                    EngineUserDetails userDetails = (EngineUserDetails) originalAuthentication.getPrincipal();
                    // Checking if we need to re-check the session, and acting accordingly
                    if (userDetails.isRecheckSessionIdNeeded()) {
                        logger.debug("Rechecking session is needed");
                        // if the sessionID has changed
                        String reqSessionID = request.getParameter("sessionID");
                        String sessionID = userDetails.getUserSessionID();
                        if (reqSessionID != null && !sessionID.equals(reqSessionID)) {
                            logger.debug("sessionID has changed, using new sessionID.");
                            sessionID = reqSessionID;
                        }
                        UsernamePasswordAuthenticationToken token = getAuthRequest(request, sessionID);
                        // if the token is null then it means we failed authentication
                        if (token == null) {
                            logger.debug("Returned token is null. Session was not valid. Setting authenticated to false");
                            authentication.setAuthenticated(false);
                        } else {
                            logger.debug("Token is not null. Setting it.");
                            metadataUserDetails.setOriginalAuthentication(token);
                        }
                    }
                }
            }
        }
        filterChain.doFilter(request, response);
    }

    /*
     * This method creates the URL connection, whether it is a secured connection or not.
     */
    private HttpURLConnection createURLConnection() throws IOException {

        logger.debug(
            String.format(
                "createURLConnection: getSessionUserGetSessionUserServletURL=%s, sslInsecure=%s, sslNoHostVerification=%s, sslTrustStoreType=%s, sslTrustStorePath=%s, sslProtocol=%s",
                getSessionUserGetSessionUserServletURL,
                sslInsecure,
                sslNoHostVerification,
                sslTrustStoreType,
                sslTrustStorePath,
                sslProtocol
            )
        );

        HttpURLConnection servletConnection = (HttpURLConnection) getSessionUserGetSessionUserServletURL.openConnection();

        if ("https".equals(getSessionUserGetSessionUserServletURL.getProtocol())) {
            HttpsURLConnection httpsConnection = (HttpsURLConnection)servletConnection;
            httpsConnection.setSSLSocketFactory(sslctx.getSocketFactory());
            if (sslInsecure || sslNoHostVerification) {
                httpsConnection.setHostnameVerifier(
                    new HostnameVerifier() {
                        @Override
                        public boolean verify(String hostname, SSLSession session) {
                            return true;
                        }
                    }
                );
            }
        }

        servletConnection.setRequestMethod("POST");
        servletConnection.setDoOutput(true);
        servletConnection.setDoInput(true);
        servletConnection.setReadTimeout(10000);
        servletConnection.setRequestProperty("Content-Type","application/x-www-form-urlencoded");

        return servletConnection;
    }

    /*
     * This method gets a sessionID, and validates it with the engine, using the servlet input URL
     */
    protected String callGetSessionUser(String sessionID) {
        try {
            // Formatting data
            String data = String.format(SESSION_DATA_FORMAT, URLEncoder.encode(sessionID, "UTF-8"));

            HttpURLConnection servletConnection = createURLConnection();

            if (servletConnection == null) {
                logger.error("Unable to create servlet connection.");
                return null;
            }

            // Sending the sessionID parameter
            try (
                OutputStream os = servletConnection.getOutputStream();
                DataOutputStream output = new DataOutputStream(os)
            ) {
                output.writeBytes(data);
                output.flush();
            }

            // Checking the result
            if (servletConnection.getResponseCode() != HttpURLConnection.HTTP_OK) {
                logger.error("GetSessionUser servlet returned " + servletConnection.getResponseCode());
                return null;
            }

            // Getting the user name
            try (
                InputStream in = servletConnection.getInputStream();
                InputStreamReader isreader = new InputStreamReader(in);
                BufferedReader reader = new BufferedReader(isreader)
            ) {
                return reader.readLine();
            }
        } catch (Exception ex) {
            logger.error(ex);
        }
        return null;
    }

    public UsernamePasswordAuthenticationToken getAuthRequest(HttpServletRequest request) {
        String sessionID = request.getParameter("sessionID");
        return getAuthRequest(request, sessionID);
    }

    /*
     * This method gets the request, and the sesionID, and resulting in the UsernamePasswordAuthenticationToken of the engine-authenticated user
     * that's logged in to the engine.
     */
    public UsernamePasswordAuthenticationToken getAuthRequest(HttpServletRequest request, String sessionID) {
        UsernamePasswordAuthenticationToken authRequest = null;
        if (sessionID != null) {
            String result = callGetSessionUser(sessionID);
            if (result == null) {
                return null;
            } else if (result.isEmpty()) {
                return null;
            }

            String userName = result;
            String password = "";

            userName = userName.trim();
            GrantedAuthority[] grantedAuthorities = new GrantedAuthority[1];
            grantedAuthorities[0] = new GrantedAuthorityImpl("ROLE_USER");

            Calendar recheckOn = Calendar.getInstance();
            recheckOn.setTime(new Date());
            recheckOn.add(Calendar.SECOND, pollingTimeout);

            EngineUserDetails userDetails = new EngineUserDetails(userName, password, grantedAuthorities, sessionID, recheckOn, true, true, true, true);
            authRequest = new UsernamePasswordAuthenticationToken(userDetails, password, grantedAuthorities);
            setDetails(request, authRequest);
        }

        return authRequest;
    }

    protected void setDetails(HttpServletRequest request, UsernamePasswordAuthenticationToken authRequest) {
        authRequest.setDetails(authenticationDetailsSource.buildDetails(request));
    }

    public void setGetSessionUserServletURL(String getSessionUserGetSessionUserServletURL) throws MalformedURLException {
        this.getSessionUserGetSessionUserServletURL = new URL(getSessionUserGetSessionUserServletURL);
    }

    public void setPollingTimeout(int pollingTimeout) {
        if (pollingTimeout >= 0) {
            this.pollingTimeout = pollingTimeout;
        } else {
            logger.debug("Input polling timeout was a negative value. Setting it to the default timeout, " + DEFAULT_POLLING_TIMEOUT);
            this.pollingTimeout = DEFAULT_POLLING_TIMEOUT;
        }
    }

    public void setSslTrustStoreType(String sslTrustStoreType) {
        this.sslTrustStoreType = sslTrustStoreType;
    }

    public void setSslTrustStorePath(String sslTrustStorePath) {
        this.sslTrustStorePath = sslTrustStorePath;
    }

    public void setSslTrustStorePassword(String sslTrustStorePassword) {
        this.sslTrustStorePassword = sslTrustStorePassword;
    }

    public void setSslProtocol(String sslProtocol) {
        this.sslProtocol = sslProtocol;
    }

    public void setSslInsecure(boolean sslInsecure) {
        this.sslInsecure = sslInsecure;
    }

    public void setSslNoHostVerification(boolean sslNoHostVerification) {
        this.sslNoHostVerification = sslNoHostVerification;
    }

    public void setAuthenticationProperties(String authenticationProperties) {
        this.authenticationProperties = authenticationProperties;
    }
}
