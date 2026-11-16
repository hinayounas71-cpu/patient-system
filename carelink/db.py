import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def cfg(key):
    """Read a setting from environment (.env) or Streamlit secrets."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        raise RuntimeError(f"Missing setting: {key}")


def anon_client():
    """Client for a logged-in user. Database ACL (RLS) applies to it."""
    return create_client(cfg("SUPABASE_URL"), cfg("SUPABASE_ANON_KEY"))


def service_client():
    """Server-only client. Used for system jobs (alerts, audit log, admin creating users).
    The service key must NEVER be shown to the browser."""
    return create_client(cfg("SUPABASE_URL"), cfg("SUPABASE_SERVICE_KEY"))
