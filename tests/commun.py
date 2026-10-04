# -*- coding: utf-8 -*-
"""Outils communs aux tests de 形音义 (Playwright, Chromium sans fenêtre).

Les tests tournent sur une copie du dépôt dont le dossier decks/ est remplacé par tests/donnees/decks :
ils ne dépendent donc pas des mots que tu ajoutes à tes listes.

Prérequis (une fois) :  py -m pip install playwright pypinyin   puis   py -m playwright install chromium
"""
import functools
import http.server
import os
import shutil
import socketserver
import sys
import threading

# la sortie passe souvent par un tube (Claude Code, redirection) : forcer l'UTF-8 pour les caractères chinois
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
SORTIE = os.path.join(TESTS, "sortie")
CAPTURES = os.path.join(SORTIE, "captures")
os.makedirs(CAPTURES, exist_ok=True)

failures = []


def check(cond, label, detail=""):
    print(("  ok   " if cond else "  ÉCHEC ") + label + ("" if cond else "  -> %s" % (detail,)))
    if not cond:
        failures.append(label)


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "max-age=600")  # ce qu'envoie GitHub Pages
        super().end_headers()


def serve(folder):
    handler = functools.partial(Handler, directory=folder)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:%d/" % httpd.server_address[1]


IGNORE = shutil.ignore_patterns(".git", "tests", "__pycache__", "node_modules", ".claude", "*.pyc")


def fresh_copy(name):
    """Copie du site (racine du dépôt) avec les listes de test figées."""
    dst = os.path.join(SORTIE, name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(REPO, dst, ignore=IGNORE)
    shutil.rmtree(os.path.join(dst, "decks"))
    shutil.copytree(os.path.join(TESTS, "donnees", "decks"), os.path.join(dst, "decks"))
    return dst


def new_page(browser, errors, scheme="light", size=(390, 844), offline_ok=False):
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=2,
                              is_mobile=True, has_touch=True, color_scheme=scheme, locale="fr-FR")
    page = ctx.new_page()

    def on_console(m):
        if m.type in ("error", "warning"):
            if offline_ok and ("Failed to fetch" in m.text or "ERR_INTERNET_DISCONNECTED" in m.text or "net::" in m.text):
                return
            errors.append("%s: %s" % (m.type, m.text))
    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append("pageerror: %s" % e))
    return ctx, page


def wait_ready(page):
    page.wait_for_function("() => typeof listsReady !== 'undefined' && listsReady && (study.cur || !document.querySelector('#done').hidden)", timeout=15000)
    page.wait_for_timeout(400)


def answer(page, g, key=False):
    """Tourne la carte si besoin, puis répond × (g = 0) ou √ (g = 1), au doigt ou au clavier (touches 1 et 2).
    Rend l'identifiant du mot noté, une fois la carte suivante prête ou l'écran de fin affiché."""
    page.wait_for_function("() => study.ready && !!study.cur")
    if page.is_visible("#turnbtn"):
        page.click("#turnbtn")
    page.wait_for_selector("#grades:not([hidden])")
    cur = page.evaluate("() => study.cur")
    if key:
        page.keyboard.press(str(g + 1))
    else:
        page.click('.grade[data-g="%d"]' % g)
    page.wait_for_function("() => !study.ready || !document.querySelector('#done').hidden")
    page.wait_for_function("() => (study.ready && !study.busy) || !document.querySelector('#done').hidden")
    return cur


def nb(s):
    """Espaces insécables (fines ou non) -> espaces ordinaires, pour comparer les textes de l'appli."""
    return (s or "").replace(" ", " ").replace(" ", " ")


def shot(page, name, full=False):
    page.screenshot(path=os.path.join(CAPTURES, name + ".png"), full_page=full)


def finish(errors):
    print("\nerreurs dans la console :", len(errors))
    for e in errors[:30]:
        print("  ", e)
    print("échecs :", failures if failures else "aucun")
    print("captures d'écran :", CAPTURES)
    sys.exit(1 if failures or errors else 0)
