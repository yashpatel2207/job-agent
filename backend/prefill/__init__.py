"""Launch Chromium, navigate to job, prefill form, wait at submit.

Runs locally on your laptop. Called by the FastAPI server when you click
"Approve and prefill" in the dashboard.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def load_profile() -> dict:
    with open(Path(__file__).parent.parent / "profile.json") as f:
        return json.load(f)


def prefill_greenhouse(page: Page, profile: dict, resume_path: str, drafted_answers: dict | None):
    p = profile["personal"]

    try:
        page.fill("input#first_name", p["first_name"])
        page.fill("input#last_name", p["last_name"])
        page.fill("input#email", p["email"])
        page.fill("input#phone", p["phone"])
    except Exception as e:
        print(f"  standard fields: {e}")

    if resume_path:
        try:
            page.set_input_files("input#resume", resume_path)
            print(f"  uploaded resume: {resume_path}")
        except Exception as e:
            print(f"  resume upload: {e}")

    for label_text, answer_key in [
        ("LinkedIn", "linkedin"),
        ("GitHub", "github"),
        ("Portfolio", "portfolio"),
        ("Website", "portfolio"),
    ]:
        try:
            locator = page.get_by_label(label_text, exact=False).first
            if locator.is_visible(timeout=500) and answer_key in p:
                locator.fill(p[answer_key])
        except Exception:
            pass

    auth = profile["work_auth"]
    try:
        sponsor_q = page.get_by_label("sponsorship", exact=False).first
        if sponsor_q.is_visible(timeout=500):
            val = "No" if not auth["needs_sponsorship_future"] else "Yes"
            sponsor_q.select_option(label=val)
    except Exception:
        pass

    if drafted_answers:
        for question, answer in drafted_answers.items():
            try:
                textarea = page.get_by_label(question, exact=False).first
                if textarea.is_visible(timeout=500):
                    textarea.fill(answer)
            except Exception:
                pass


def prefill_lever(page: Page, profile: dict, resume_path: str, drafted_answers: dict | None):
    p = profile["personal"]

    try:
        page.fill("input[name='name']", f"{p['first_name']} {p['last_name']}")
        page.fill("input[name='email']", p["email"])
        page.fill("input[name='phone']", p["phone"])
        page.fill("input[name='org']", profile.get("current_company", ""))
        page.fill("input[name='urls[LinkedIn]']", p["linkedin"])
        page.fill("input[name='urls[GitHub]']", p["github"])
    except Exception as e:
        print(f"  standard fields: {e}")

    if resume_path:
        try:
            page.set_input_files("input[name='resume']", resume_path)
        except Exception as e:
            print(f"  resume: {e}")


def prefill_ashby(page: Page, profile: dict, resume_path: str, drafted_answers: dict | None):
    p = profile["personal"]

    try:
        page.get_by_label("Full name", exact=False).fill(f"{p['first_name']} {p['last_name']}")
        page.get_by_label("Email", exact=False).fill(p["email"])
        page.get_by_label("Phone", exact=False).fill(p["phone"])
        page.get_by_label("LinkedIn", exact=False).fill(p["linkedin"])
    except Exception as e:
        print(f"  standard fields: {e}")

    if resume_path:
        try:
            page.set_input_files("input[type='file']", resume_path)
        except Exception as e:
            print(f"  resume: {e}")


def prefill_workday(page: Page, profile: dict, resume_path: str, drafted_answers: dict | None, tenant: str):
    creds = profile.get("workday_credentials", {})
    p = profile["personal"]

    try:
        if page.get_by_text("Sign In", exact=False).is_visible(timeout=2000):
            page.fill("input[data-automation-id='email']", p["email"])
            page.fill("input[data-automation-id='password']", creds.get("default_password", ""))
            page.click("button[data-automation-id='signInSubmitButton']")
            page.wait_for_load_state("networkidle")
    except Exception:
        pass

    try:
        page.click("a[data-automation-id='adventureButton']", timeout=3000)
    except Exception:
        pass

    try:
        page.fill("input[data-automation-id='legalNameSection_firstName']", p["first_name"])
        page.fill("input[data-automation-id='legalNameSection_lastName']", p["last_name"])
        page.fill("input[data-automation-id='email']", p["email"])
        page.fill("input[data-automation-id='phone-number']", p["phone"])
        page.fill("input[data-automation-id='addressSection_addressLine1']", p.get("address", ""))
        page.fill("input[data-automation-id='addressSection_city']", p.get("city", ""))
        page.fill("input[data-automation-id='addressSection_postalCode']", p.get("zip", ""))
    except Exception as e:
        print(f"  workday personal: {e}")

    if resume_path:
        try:
            page.set_input_files("input[data-automation-id='file-upload-input-ref']", resume_path)
        except Exception as e:
            print(f"  workday resume: {e}")


def prefill(apply_url: str, ats: str, resume_path: str, drafted_answers: dict | None = None, workday_tenant: str | None = None):
    """Main entry point. Opens browser, fills form, leaves it open for user review."""
    profile = load_profile()

    session_dir = SESSIONS_DIR / ats
    session_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False,
            viewport={"width": 1400, "height": 900},
        )
        page = ctx.new_page()
        page.goto(apply_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        if ats == "greenhouse":
            prefill_greenhouse(page, profile, resume_path, drafted_answers)
        elif ats == "lever":
            prefill_lever(page, profile, resume_path, drafted_answers)
        elif ats == "ashby":
            prefill_ashby(page, profile, resume_path, drafted_answers)
        elif ats == "workday":
            prefill_workday(page, profile, resume_path, drafted_answers, workday_tenant or "")
        else:
            print(f"No prefill handler for {ats}, leaving form blank")

        print("\n✓ Form prefilled. Review, edit, and submit manually.")
        print("  Press Ctrl+C in this terminal when done to close the browser.")

        try:
            page.wait_for_event("close", timeout=0)
        except KeyboardInterrupt:
            pass
        finally:
            ctx.close()
