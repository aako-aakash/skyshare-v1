import os
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv



load_dotenv()


def get_secret(name, default=None):
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        value = st.secrets.get(name)
        if value is not None:
            return value
    except Exception:
        pass

    return os.getenv(name, default)


API_URL = get_secret(
    "API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

API_KEY = get_secret("API_KEY")

LINKEDIN_URL = "https://www.linkedin.com/in/aako-aakash/"
GITHUB_URL = "https://github.com/aako-aakash"

APP_NAME = "SKYSHARE"
APP_VERSION = "v1.0"
TAGLINE = "Capture. Share. Connect. 📸🎥"
LOGO_PATH = Path(__file__).resolve().parent / "skyshare_logo.png"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SkyShare",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)


if not API_KEY:
    st.error(
        "⚠️ SkyShare API key is not configured. "
        "Add `API_KEY` to Streamlit Cloud Secrets or your local `.env`."
    )


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "token": None,
    "user": None,
    "page": "Feed",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# API HELPERS
# ============================================================

def api_headers():
    headers = {}

    if API_KEY:
        headers["X-API-Key"] = API_KEY

    if st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    return headers


def api_request(method, endpoint, **kwargs):
    try:
        headers = kwargs.pop("headers", {}) or {}
        merged_headers = api_headers()
        merged_headers.update(headers)

        return requests.request(
            method,
            f"{API_URL}{endpoint}",
            headers=merged_headers,
            timeout=60,
            **kwargs,
        )
    except requests.exceptions.ConnectionError:
        st.error(
            "❌ **Backend connection failed.**\n\n"
            f"FastAPI URL: `{API_URL}`\n\n"
            "Make sure the backend is running and the API URL is correct."
        )
        return None
    except requests.exceptions.Timeout:
        st.error(
            "⏱️ **Request timed out.**\n\n"
            "The backend took too long to respond. Please try again."
        )
        return None
    except requests.exceptions.RequestException as exc:
        st.error(f"❌ **Request failed:** {exc}")
        return None


def response_detail(response, fallback):
    try:
        data = response.json()
        detail = data.get("detail")

        if isinstance(detail, list):
            messages = []
            for item in detail:
                if isinstance(item, dict):
                    messages.append(item.get("msg", str(item)))
                else:
                    messages.append(str(item))
            return " ".join(messages)

        if detail:
            return str(detail)
    except (ValueError, AttributeError):
        pass

    return response.text or fallback


# ============================================================
# AUTH
# ============================================================

def get_current_user():
    response = api_request(
        "GET",
        "/users/me",
        headers=api_headers(),
    )

    if response is not None and response.ok:
        return response.json()

    return None


def register(email, password):
    response = api_request(
        "POST",
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    if response is None:
        return False

    if response.status_code in (200, 201):
        return True

    st.error(
        f"❌ **Registration failed:** "
        f"{response_detail(response, 'Please try again.')}"
    )
    return False


def login(email, password):
    response = api_request(
        "POST",
        "/auth/jwt/login",
        data={
            "username": email,
            "password": password,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    if response is None:
        return False

    if response.ok:
        data = response.json()
        token = data.get("access_token")

        if not token:
            st.error("❌ No access token was returned by the backend.")
            return False

        st.session_state.token = token
        st.session_state.user = get_current_user()

        if st.session_state.user is None:
            st.session_state.token = None
            st.error("❌ Login succeeded, but the user profile could not be loaded.")
            return False

        return True

    st.error(
        f"❌ **Login failed:** "
        f"{response_detail(response, 'Invalid email or password.')}"
    )
    return False


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.page = "Feed"
    st.rerun()


# ============================================================
# POSTS
# ============================================================

def fetch_feed():
    response = api_request(
        "GET",
        "/feed",
        headers=api_headers(),
    )

    if response is None:
        return []

    if response.ok:
        return response.json().get("posts", [])

    if response.status_code == 401:
        logout()

    st.error(
        f"❌ **Could not load the feed:** "
        f"{response_detail(response, 'Please try again.')}"
    )
    return []


def upload_post(uploaded_file, caption):
    response = api_request(
        "POST",
        "/upload",
        headers=api_headers(),
        files={
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        },
        data={
            "caption": caption,
        },
    )

    if response is None:
        return False

    if response.status_code in (200, 201):
        return True

    st.error(
        f"❌ **Upload failed:** "
        f"{response_detail(response, 'Please try again.')}"
    )
    return False


def delete_post(post_id):
    response = api_request(
        "DELETE",
        f"/posts/{post_id}",
        headers=api_headers(),
    )

    if response is None:
        return False

    if response.ok:
        return True

    st.error(
        f"❌ **Delete failed:** "
        f"{response_detail(response, 'Please try again.')}"
    )
    return False


# ============================================================
# DISPLAY HELPERS
# ============================================================

def format_date(value):
    if not value:
        return ""

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return parsed.strftime("%d %b %Y • %I:%M %p")
    except (ValueError, TypeError):
        return str(value)


def get_display_name(email):
    if not email:
        return "SkyShare User"

    return email.split("@")[0].replace(".", " ").replace("_", " ").title()


def render_section_header(title, description=None, icon=""):
    st.title(f"{icon} {title}".strip())

    if description:
        st.caption(description)


def render_empty_state():
    st.info(
        "📸 **Your feed is waiting for its first moment.**\n\n"
        "Create a post and start building your SkyShare collection."
    )

    if st.button(
        "✨ Create the first post",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.page = "Create Post"
        st.rerun()


# ============================================================
# AUTHENTICATION PAGE
# ============================================================

def authentication_page():
    st.write("")
    st.write("")

    hero_left, hero_right = st.columns([1.45, 1], gap="large")

    with hero_left:
        logo_col, title_col = st.columns([1, 2.2], vertical_alignment="center")

        with logo_col:
            if LOGO_PATH.exists():
                st.image(LOGO_PATH, width=120)
            else:
                st.write("☁️")

        with title_col:
            st.title("SKYSHARE")
            st.caption(TAGLINE)

        st.write(
            "A simple space for sharing the photos and videos "
            "that matter to you."
        )

        st.write("")

        feature_1, feature_2, feature_3 = st.columns(3)

        with feature_1:
            st.metric("📸", "Photos", "Share")

        with feature_2:
            st.metric("🎥", "Videos", "Share")

        with feature_3:
            st.metric("☁️", "Cloud", "Powered")

        st.write("")
        st.caption(
            f"{APP_VERSION} • Streamlit Edition • "
            "Built as the first SkyShare release"
        )

    with hero_right:
        st.subheader("Welcome to SkyShare 👋")
        st.caption("Sign in to your account or create a new one.")

        login_tab, register_tab = st.tabs(
            ["🔐 Login", "✨ Create Account"]
        )

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                    key="login_email",
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="login_password",
                )

                submitted = st.form_submit_button(
                    "Login to SkyShare",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                email = email.strip()

                if not email or not password:
                    st.warning("Please enter both email and password.")
                elif login(email, password):
                    st.success("Welcome back! 🎉")
                    st.rerun()

        with register_tab:
            with st.form("register_form", clear_on_submit=False):
                email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                    key="register_email",
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Create a password",
                    key="register_password",
                )

                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Repeat your password",
                    key="register_confirm_password",
                )

                submitted = st.form_submit_button(
                    "Create SkyShare Account",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                email = email.strip()

                if not email or not password or not confirm_password:
                    st.warning("Please fill in all fields.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                elif register(email, password):
                    st.success(
                        "Account created successfully! "
                        "Switch to Login to continue. 🎉"
                    )


# ============================================================
# SIDEBAR
# ============================================================

def sidebar():
    user = st.session_state.user or {}
    email = user.get("email", "SkyShare User")
    display_name = get_display_name(email)

    with st.sidebar:
        logo_col, title_col = st.columns([1, 1.9], vertical_alignment="center")

        with logo_col:
            if LOGO_PATH.exists():
                st.image(LOGO_PATH, width=72)
            else:
                st.write("☁️")

        with title_col:
            st.markdown("### SKYSHARE")
            st.caption(TAGLINE)

        st.divider()

        st.write("👋 **Welcome back**")
        st.write(f"**{display_name}**")
        st.caption(email)

        st.divider()

        st.session_state.page = st.radio(
            "Navigate",
            ["Feed", "Create Post"],
            index=0 if st.session_state.page == "Feed" else 1,
            label_visibility="collapsed",
        )

        st.divider()

        if st.button(
            "🔄 Refresh Feed",
            use_container_width=True,
        ):
            st.rerun()

        if st.button(
            "🚪 Logout",
            use_container_width=True,
        ):
            logout()

        st.divider()

        st.caption(f"SkyShare {APP_VERSION}")
        st.caption("Capture. Share. Connect.")


# ============================================================
# POST CARD
# ============================================================

def render_post(post):
    post_id = post.get("id")
    email = post.get("email", "SkyShare User")
    display_name = get_display_name(email)
    caption = (post.get("caption") or "").strip()
    url = post.get("url")
    file_type = post.get("file_type", "image")
    created_at = format_date(post.get("created_at"))
    is_owner = post.get("is_owner", False)

    with st.container(border=True):
        header_left, header_right = st.columns([5, 1])

        with header_left:
            st.subheader(f"👤 {display_name}")

            metadata = email
            if created_at:
                metadata += f"  •  {created_at}"

            st.caption(metadata)

        with header_right:
            st.caption(
                "🎥 VIDEO" if file_type == "video" else "📸 PHOTO"
            )

        if caption:
            st.write(caption)

        if url:
            if file_type == "video":
                st.video(url)
            else:
                st.image(
                    url,
                    use_container_width=True,
                )
        else:
            st.warning("⚠️ Media URL is unavailable.")

        if is_owner and post_id:
            st.divider()

            delete_left, delete_right = st.columns([5, 1])

            with delete_right:
                if st.button(
                    "🗑️ Delete",
                    key=f"delete_{post_id}",
                    use_container_width=True,
                ):
                    if delete_post(post_id):
                        st.success("Post deleted successfully.")
                        st.rerun()


# ============================================================
# FEED PAGE
# ============================================================

def feed_page():
    render_section_header(
        "SkyShare Feed",
        "Discover photos and videos shared by the SkyShare community.",
        "🏠",
    )

    posts = fetch_feed()

    photo_count = sum(
        1 for post in posts if post.get("file_type") != "video"
    )
    video_count = sum(
        1 for post in posts if post.get("file_type") == "video"
    )

    stat_1, stat_2, stat_3, stat_4 = st.columns(4)

    with stat_1:
        st.metric("📝 Posts", len(posts))

    with stat_2:
        st.metric("📸 Photos", photo_count)

    with stat_3:
        st.metric("🎥 Videos", video_count)

    with stat_4:
        if st.button(
            "🔄 Refresh",
            use_container_width=True,
        ):
            st.rerun()

    st.divider()

    if not posts:
        render_empty_state()
        return

    for post in posts:
        render_post(post)
        st.write("")


# ============================================================
# CREATE POST PAGE
# ============================================================

def create_post_page():
    render_section_header(
        "Create a New Post",
        "Share a photo or video with your SkyShare community.",
        "✨",
    )

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.subheader("1. Choose your media")

        uploaded_file = st.file_uploader(
            "Upload an image or video",
            type=[
                "jpg",
                "jpeg",
                "png",
                "gif",
                "webp",
                "mp4",
                "mov",
                "avi",
                "webm",
                "mkv",
            ],
            help="Supported images and common video formats.",
        )

        st.subheader("2. Add a caption")

        caption = st.text_area(
            "Caption",
            placeholder="Tell the community something about this moment...",
            max_chars=500,
            height=140,
        )

        st.caption(f"{len(caption)}/500 characters")

        share_button = st.button(
            "🚀 Share on SkyShare",
            type="primary",
            use_container_width=True,
            disabled=uploaded_file is None,
        )

    with right:
        st.subheader("Preview")

        if uploaded_file:
            file_type = uploaded_file.type or ""

            if file_type.startswith("video/"):
                st.video(uploaded_file)
            else:
                st.image(
                    uploaded_file,
                    use_container_width=True,
                )

            st.caption(f"📎 {uploaded_file.name}")

            if uploaded_file.size:
                size_mb = uploaded_file.size / (1024 * 1024)
                st.caption(f"File size: {size_mb:.2f} MB")
        else:
            st.info(
                "Your selected media will appear here as a preview."
            )

        st.divider()

        st.caption(
            "💡 **Tip:** Keep captions short and meaningful. "
            "You can always create another post later."
        )

    if share_button:
        if not uploaded_file:
            st.warning("Please choose an image or video first.")
            return

        with st.spinner("☁️ Uploading your moment..."):
            success = upload_post(
                uploaded_file,
                caption.strip(),
            )

        if success:
            st.success("Your post is live on SkyShare! 🎉")
            st.session_state.page = "Feed"
            st.rerun()


# ============================================================
# FOOTER
# ============================================================

def footer():
    st.divider()

    left, center, right = st.columns([2.2, 1.2, 1.2], vertical_alignment="center")

    with left:
        footer_logo_col, footer_text_col = st.columns(
            [0.65, 3.35],
            vertical_alignment="center",
        )

        with footer_logo_col:
            if LOGO_PATH.exists():
                st.image(LOGO_PATH, width=58)

        with footer_text_col:
            st.caption(
                f"{APP_NAME} — {TAGLINE}"
            )
            st.caption(
                f"Built by AAKASH • {APP_VERSION} • "
                "Streamlit Edition"
            )

    with center:
        st.link_button(
            "LinkedIn ↗",
            LINKEDIN_URL,
            use_container_width=True,
        )

    with right:
        st.link_button(
            "GitHub ↗",
            GITHUB_URL,
            use_container_width=True,
        )


# ============================================================
# MAIN
# ============================================================

def main():
    if not LOGO_PATH.exists():
        st.warning(
            "Logo asset not found. Place `skyshare_logo_trimmed.png` "
            "next to this Streamlit file."
        )

    if not st.session_state.token:
        authentication_page()
    else:
        sidebar()

        if st.session_state.page == "Create Post":
            create_post_page()
        else:
            feed_page()

    footer()


if __name__ == "__main__":
    main()
