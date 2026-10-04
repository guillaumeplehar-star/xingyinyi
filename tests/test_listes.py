# -*- coding: utf-8 -*-
"""Listes créées sur le téléphone, exemple sur la face 形, publication sur GitHub (API simulée, avec le délai
de mise en ligne de GitHub Pages ; la liste publiée garde la progression de ses mots, seau compris, et la file
n'a plus d'identifiant du téléphone), bouton de mise à jour. Lancer depuis la racine du dépôt :  py tests\\test_listes.py
"""
import json
import os
import re

from playwright.sync_api import sync_playwright

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish


def main():
    errors = []
    site = fresh_copy("site-phone")
    global ORIG_H3
    ORIG_H3 = open(os.path.join(site, "decks", "hsk3.tsv"), encoding="utf-8").read()
    httpd, url = serve(site)
    calls = []
    repo = {}
    for folder, _, names in os.walk(os.path.join(site, "decks")):
        for n in names:
            full = os.path.join(folder, n)
            repo[os.path.relpath(full, site).replace(os.sep, "/")] = open(full, encoding="utf-8").read()

    def deploy():
        for path, content in repo.items():
            # newline="": the files served must be byte for byte what was published (no \r\n on Windows)
            open(os.path.join(site, *path.split("/")), "w", encoding="utf-8", newline="").write(content)
        for n in os.listdir(os.path.join(site, "decks")):
            if "decks/" + n not in repo:
                os.remove(os.path.join(site, "decks", n))

    def api(route):
        req = route.request
        u = req.url.split("api.github.com", 1)[1]
        calls.append((req.method, u, req.post_data))
        path = u.split("?")[0]
        def ok(obj):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(obj))
        if path == "/repos/u/xingyinyi":
            return ok({"default_branch": "main", "permissions": {"push": True}})
        if path == "/repos/u/xingyinyi/git/ref/heads/main":
            return ok({"object": {"sha": "c0"}})
        if path == "/repos/u/xingyinyi/git/commits/c0":
            return ok({"tree": {"sha": "t0"}})
        m = re.match(r"/repos/u/xingyinyi/contents/(.+)$", path)
        if m:
            if m.group(1) in repo:
                return route.fulfill(status=200, content_type="text/plain; charset=utf-8", body=repo[m.group(1)])
            return route.fulfill(status=404, content_type="application/json", body='{"message":"Not Found"}')
        if path.endswith("/git/trees"):
            for e in json.loads(req.post_data)["tree"]:
                if e.get("sha", "x") is None:
                    repo.pop(e["path"], None)
                else:
                    repo[e["path"]] = e["content"]
            return ok({"sha": "t1"})
        if path.endswith("/git/commits"):
            return ok({"sha": "c1"})
        if path.endswith("/git/refs/heads/main"):
            return ok({"object": {"sha": "c1"}})
        route.fulfill(status=500, body="unexpected")

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx, page = new_page(b, errors)
        page.route("https://api.github.com/**", api)
        page.goto(url)
        wait_ready(page)
        # example on the 形 face
        fx = page.evaluate("() => { const f = document.querySelector('#stage .face[data-face=\"0\"] .form-ex'); return f ? f.textContent : null; }")
        w = page.evaluate("() => BYID.get(study.cur).e || null")
        check((fx is not None) == (w is not None) and (fx is None or fx == w), "example sentence on the 形 face", (fx, w))
        shot(page, "phone-01-form-example")
        # create a list, add two words into it
        page.click('.tab[data-view="words"]')
        page.click("#wdeck [data-newlist]")
        page.fill("#l-n", "Cours du mardi")
        page.click("#lform button[type=submit]")
        page.wait_for_timeout(200)
        st = page.evaluate("() => ({ lists: state.lists.map(x => x.nom), wdeck })")
        check(st["lists"] == ["Cours du mardi"] and st["wdeck"].startswith("p-"), "list created and selected", st)
        page.click('#listbar [data-la="add"]')
        page.fill("#f-h", "复印")
        page.fill("#f-p", "fu4yin4")
        page.fill("#f-f", "photocopier")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        page.click("#btn-add")
        page.fill("#f-h", "打印")
        page.fill("#f-p", "dǎyìn")
        page.fill("#f-f", "imprimer")
        page.click(".more summary")
        page.fill("#f-e", "我要打印这张照片。")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        shot(page, "phone-02-list")
        page.click("#btn-add")
        page.fill("#f-h", "图书馆")
        page.fill("#f-p", "túshūguǎn")
        page.fill("#f-f", "bibliothèque")
        page.wait_for_timeout(100)
        check("Aussi dans HSK 3" in page.inner_text("#f-hh"), "hint: also in HSK 3")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        st = page.evaluate("() => ({ inList: LISTBYID.get(wdeck).words.map(w => w.h) })")
        check(st["inList"] == ["复印", "打印", "图书馆"], "words added to the new list (a HSK word included)", st)
        page.click("#btn-export")
        page.wait_for_timeout(200)
        exp = page.inner_text("#sheet-body")
        check("nouvelle-liste cours-du-mardi" in exp and "decks/cours-du-mardi.tsv" in exp, "export explains where the lines go", exp[:300])
        page.click("#sheet .close")
        # a word in a second list via the form's "new list" option, then delete that list
        page.click("#btn-add")
        page.select_option("#f-l", "__new")
        page.fill("#f-ln", "À jeter")
        page.fill("#f-h", "安排")
        page.fill("#f-p", "an1pai2")
        page.fill("#f-f", "organiser")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        jid = page.evaluate("() => state.lists.find(x => x.nom === 'À jeter').id")
        page.click('#wdeck button[data-deck="%s"]' % jid)
        page.click('#listbar [data-la="delete"]')
        page.click('#listbar [data-la="delete-yes"]')
        page.wait_for_timeout(200)
        st = page.evaluate("() => ({ lists: state.lists.map(x => x.nom), words: state.custom.map(w => w.h) })")
        check(st == {"lists": ["Cours du mardi"], "words": ["复印", "打印", "图书馆"]}, "list deleted with its words", st)
        # learn one of them, edit a HSK word
        page.evaluate("() => { const w = state.custom.find(x => x.h === '打印'); applyGrade(w.id, true); state.edits['hsk3:还'] = { f: 'rendre ; rembourser' }; save(); rebuildDeck(); }")
        # connect to GitHub and publish
        page.click('.tab[data-view="settings"]')
        page.fill("#gh-repo", "u/xingyinyi")
        page.fill("#gh-token", "github_pat_test")
        page.click('[data-gh="login"]')
        page.wait_for_selector('[data-gh="publish"]')
        shot(page, "phone-03-github", full=False)
        page.click('[data-gh="publish"]')
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('Publié')", timeout=8000)
        msg = page.inner_text("#toast")
        print("  toast:", msg)
        tree = [json.loads(c[2]) for c in calls if c[0] == "POST" and c[1].endswith("/git/trees")][0]
        files = {e["path"]: e.get("content") for e in tree["tree"]}
        cfg = json.loads(files["decks/decks.json"])
        new = [l for l in cfg["listes"] if l["nom"] == "Cours du mardi"]
        check(tree["base_tree"] == "t0" and new and new[0]["fichier"] == "cours-du-mardi.tsv" and cfg["listes"][0]["nom"] == "Cours du mardi",
              "new list declared first in decks.json", cfg["listes"][:2])
        check(new and set(new[0]) == {"id", "nom", "fichier", "actif"}, "new decks.json entry without mode nor parJour", new)
        body = files.get("decks/cours-du-mardi.tsv", "")
        check("复印\tfùyìn\tphotocopier" in body and "打印\tdǎyìn\timprimer\t\t\t我要打印这张照片。" in body and "图书馆\ttúshūguǎn" in body and body.startswith("# 形音义"), "list file written", body[-200:])
        h3 = files.get("decks/hsk3.tsv", "")
        check("\trendre ; rembourser\t" in h3 and h3.count("\n") == ORIG_H3.count("\n"),
              "correction written into hsk3.tsv, nothing else touched")
        patch = [c for c in calls if c[0] == "PATCH"]
        check(patch and json.loads(patch[0][2])["sha"] == "c1", "branch moved to the new commit")
        after = page.evaluate("() => ({ lists: state.lists.length, custom: state.custom.length, card: state.cards['cours-du-mardi:打印'], edits: Object.keys(state.edits).length, list: LISTBYID.get('cours-du-mardi') && LISTBYID.get('cours-du-mardi').words.length })")
        check(after["lists"] == 0 and after["custom"] == 0 and after["card"] and after["card"]["b"] == 1 and after["edits"] == 0 and after["list"] == 3,
              "phone list became a repo list, progress kept (bucket 1)", after)
        ln = page.evaluate("""() => { const L = [study.cur, ...study.queue].filter(Boolean);
            return { stale: L.filter(id => /^(u-|p-)/.test(id)), cards: Object.keys(state.cards).filter(id => /^(u-|p-)/.test(id)),
              fresh: ['复印', '图书馆'].map(h => L.includes('cours-du-mardi:' + h)), learnt: L.includes('cours-du-mardi:打印') }; }""")
        check(ln == {"stale": [], "cards": [], "fresh": [True, True], "learnt": False},
              "line after the merge: no phone id left, the published words waiting for their first pass", ln)
        # GitHub Pages has not deployed yet: the old files must not undo the publication
        page.evaluate("() => refreshLists(false, true)")
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('pas encore')", timeout=8000)
        st = page.evaluate("() => ({ list: !!LISTBYID.get('cours-du-mardi'), f: BYID.get('hsk3:还').f })")
        check(st["list"] and "rembourser" in st["f"], "stale GitHub Pages ignored after publishing", st)
        deploy()
        page.evaluate("() => refreshLists(false, true)")
        page.wait_for_timeout(800)
        st = page.evaluate("() => ({ list: !!LISTBYID.get('cours-du-mardi'), guard: localStorage.getItem('xingyinyi.publie') })")
        check(st["list"] and st["guard"] is None, "deployed files accepted, guard cleared", st)
        # delete a repo list from the phone
        page.click('[data-gdel="cours-du-mardi"]')
        page.click('[data-gdel-yes="cours-du-mardi"]')
        page.wait_for_function("() => !LISTBYID.has('cours-du-mardi')", timeout=8000)
        deploy()
        tree2 = [json.loads(c[2]) for c in calls if c[0] == "POST" and c[1].endswith("/git/trees")][-1]
        dele = [e for e in tree2["tree"] if e.get("sha", "x") is None]
        check(dele and dele[0]["path"] == "decks/cours-du-mardi.tsv", "repo list deleted from the phone", tree2["tree"])
        # app update button
        page.click("#app-update")
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('à jour')", timeout=8000)
        check(True, "update button answers")
        shot(page, "phone-04-settings")
        ctx.close()
        b.close()
    httpd.shutdown()
    finish(errors)


if __name__ == "__main__":
    main()
