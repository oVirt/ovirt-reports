package org.ovirt.authentication;

import java.util.Calendar;
import java.util.Collection;
import java.util.Date;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

public class EngineUserDetails implements UserDetails {

    public EngineUserDetails(String userName,
            String password,
            Collection<GrantedAuthority> authorities,
            String userSessionID,
            Calendar recheckSessionIdOn,
            boolean isAccountNonExpired,
            boolean isAccountNonLocked,
            boolean isCredentialsNonExpired,
            boolean isEnabled) {
        super();
        this.userName = userName;
        this.password = password;
        this.authorities = authorities;
        this.userSessionID = userSessionID;
        this.recheckSessionIdOn = recheckSessionIdOn;
        this.isAccountNonExpired = isAccountNonExpired;
        this.isAccountNonLocked = isAccountNonLocked;
        this.isCredentialsNonExpired = isCredentialsNonExpired;
        this.isEnabled = isEnabled;
    }

    private static final long serialVersionUID = -7928501868572473559L;

    private String userName;
    private String password;
    private Collection<GrantedAuthority> authorities;
    private String userSessionID;
    private Calendar recheckSessionIdOn;
    private boolean isAccountNonExpired;
    private boolean isAccountNonLocked;
    private boolean isCredentialsNonExpired;
    private boolean isEnabled;

    @Override
    public Collection<GrantedAuthority> getAuthorities() {
        return authorities;
    }

    @Override
    public String getPassword() {
        return password;
    }

    @Override
    public String getUsername() {
        return userName;
    }

    @Override
    public boolean isAccountNonExpired() {
        return isAccountNonExpired;
    }

    @Override
    public boolean isAccountNonLocked() {
        return isAccountNonLocked;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return isCredentialsNonExpired;
    }

    @Override
    public boolean isEnabled() {
        return isEnabled;
    }

    public boolean isRecheckSessionIdNeeded() {
        Calendar currDate = Calendar.getInstance();
        currDate.setTime(new Date());
        return currDate.after(recheckSessionIdOn);
    }

    public String getUserSessionID() {
        return userSessionID;
    }

    public void setUserSessionID(String userSessionID) {
        this.userSessionID = userSessionID;
    }

}
