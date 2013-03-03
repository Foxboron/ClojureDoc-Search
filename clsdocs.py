#!/usr/bin/env python

"""
Copyright (c) 2012, Morten "Foxboron" Linderud
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 - Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

 - Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

 - Neither the name of Morten "Foxboron" Linderud nor the names of its contributors
   may be used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sublime
import sublime_plugin
import urllib2
from bs4 import BeautifulSoup
import webbrowser
import re

def request(var):
    var = "http://clojuredocs.org/search?q=%s" % var
    req = urllib2.urlopen(var).read()
    return req


def content_request(url):
    req = urllib2.urlopen(url).read()
    return req


def bs4_parse(var):
    """Parses out the indvidual search item"""
    var = request(var)
    soup = BeautifulSoup(var)
    stuff = soup.body.find_all("div", "search_result")
    items = []
    sites = []
    for i in stuff:
        item, web = parse_list(i)
        items.append(item)
        sites.append(web)
    return (items, sites)


def parse_list(item):
    """Parses out the main search results."""
    dic = []
    #What
    dic.append(str(item.find("a").text))
    #Doc
    p = item.find("p", "doc").text
    if p:
        if len(p) > 66:
            p = p[:66] + "....."
        dic.append("".join([i.replace("\n", " ") for i in p]))
    else:
        dic.append("No Documentation")
    #What lib
    dic.append("Namespace: %s" % str(item.find("span", "ns").a.text))
    #Available exmaples
    dic.append("Available Examples: %s" % str(item.find("span", "examples_count").text.split()[0]))
    #http
    web = item.find("span", "linktext").text
    return (dic, web)


def seealso_search(url):
    """Searches the 'See Also...' part. """
    v = content_request(url)
    soup = BeautifulSoup(v)
    stuff = soup.body.find_all("li", "see_also_item")
    items = []
    sites = []
    for i in stuff:
        item, web = new_parse(i)
        items.append(item)
        sites.append(web)
    return (items, sites)


def new_parse(n):
    """Parsing the HTML 'see also...' links and names."""
    http = "http://clojuredocs.org"
    dic = []
    #Name
    dic.append(str(n.find("span", "name").text))
    #Doc
    p = n.find("p", "shortdoc").text
    if p:
        if len(p) > 66:
            p = p[:66] + "....."
        dic.append("".join([i.replace("\n", " ") for i in p]))
    else:
        dic.append("No Documentation")
    #Namespace
    dic.append("Namespace: %s" % str(n.find("span", "ns").text[:-1]))
    #http
    web = http + n.find("a").get("href")
    return (dic, web)


def parse_source(url):
    """Parsing source"""
    v = content_request(url)
    soup = BeautifulSoup(v)
    stuff = soup.find("div", "source_content")
    l = []
    if not stuff:
        ret = " \n" + "NO SOURCE! OMG!\n"
        l.append(ret.split("\n"))
        return l
    stuff = stuff.find("pre", "brush: clojure")
    ret = "Source:        \n" + stuff.text
    l.append(ret.split("\n"))
    return l


def parse_example(url):
    """Parsing examples"""
    v = content_request(url)
    soup = BeautifulSoup(v)
    stuff = soup.find_all("div", "hidden plain_content")
    l = []
    if not stuff:
        ret = " \n" + "NO EXAMPLES! OMG!\n"
        l.append(ret.split("\n"))
        return l
    num = 1
    for i in stuff:
        ret = "Example #" + str(num) + ":    \n" + i.text.rstrip("\n")
        l.append(ret.split("\n"))
        num += 1
    return l


def parse_doc(url):
    """Parsing the documentation."""
    v = content_request(url)
    soup = BeautifulSoup(v)
    stuff = soup.find("div", "doc").find("div", "content")
    for e in stuff.findAll("br"):
        e.replace_with("\n")
    l = []
    if not stuff:
        ret = " \n" + "NO DOCS! OMG GO FIX NAOW!!\n"
        l.append(ret.split("\n"))
        return l
    ret = "Documentation: \n" + stuff.text
    l.append(ret.split("\n"))
    return l


class CljSearchCommand(sublime_plugin.WindowCommand):
    def run(self):
        """Runs the initial plugin"""
        self.window.show_input_panel("Search", "", self.on_done, None, None)

    def on_done(self, search):
        """Fetches the search results"""
        self.res, self.search_links = bs4_parse(search)
        for i in range(0, len(self.res)):
            if search == self.res[i][0]:
                self.panel_items = self.res
                self.done(i)
                return
        self.search(s=self.res, link=self.search_links)

    def search(self, s=None, link=None):
        """Created a seperate method for the search.
           Thus we can apply a back function"""
        if s:
            self.panel_items = s
        if link:
            self.search_links = link
        self.window.show_quick_panel(self.panel_items, self.done)

    def done(self, num):
        """Main menu!"""
        if num == -1: return
        options = [
                    "View Docs",
                    "View Source",
                    "View Examples",
                    "See Also...",
                    "Open website",
                    "Back"
                    ]
        self.num = num
        self.window.show_quick_panel(options, self.selected_item)

    def doc_view(self, lis):
        """Directs back to the sub menu"""
        self.inser_content = lis
        self.window.show_quick_panel(lis, self.select_edit)

    def doc_check(self, lis):
        """Returns directly back to the main menu."""
        self.window.show_quick_panel(lis, self.return_from_doc)

    def return_from_doc(self, num):
        """Because of the depedancy on 'self.num' to actually know where we are
        I had to do this....yeah i know...dat method...."""
        self.done(self.num)

    def select_edit(self, num):
        """Sub menu!"""
        if num == -1: return self.done(self.num)
        self.selected_example = num
        options = [
                    "Insert",
                    "Back"
                    ]
        self.window.show_quick_panel(options, self.inser_back)

    def inser_back(self, num):
        """2nd menu directing the Insert/Back options."""
        if num == 0:
            buffr = "\n".join(self.inser_content[self.selected_example])
            view = self.window.active_view()
            e = view.begin_edit()
            for r in view.sel():
                if r.empty():
                    view.insert(e, r.a, buffr[16:])
                else:
                    view.replace(e, r,   buffr[16:])
            view.end_edit(e)
        if num == 1:
            self.done(self.num)

    def selected_item(self, num):
        """1st menu. Directing the options to the main menu."""
        if num == -1:
            self.search(s=self.res, link=self.search_links)
        if num == 0:
            self.doc_check(parse_doc(self.search_links[self.num]))
        if num == 1:
            self.doc_view(parse_source(self.search_links[self.num]))
        if num == 2:
            self.doc_view(parse_example(self.search_links[self.num]))
        if num == 3:
            self.see_also, self.see_also_links = seealso_search(self.search_links[self.num])
            self.search(s=self.see_also, link=self.see_also_links)
        if num == 4:
            webbrowser.open(self.search_links[self.num])
        if num == 5:
            self.search()


# Select word hack from bronson :D
# https://github.com/bronson/GotoFile


def expanded_selection(view, line, left, right):
    pat = re.compile('^[A-Za-z0-9_.-?*]+$')
    while left > line.begin() and re.match(pat, view.substr(left - 1)):
        left -= 1
    while right < line.end() and re.match(pat, view.substr(right)):
        right += 1
    return view.substr(sublime.Region(left, right))


def selection_words(view):
    words = []
    for sel in view.sel():
        if sel.empty():
            line = view.line(sel.begin())
            words.append(expanded_selection(view, line, sel.begin(), sel.begin()))
        else:
            words.append(view.substr(sel))
    # print "FILES: " + repr(words)
    return words


class GotoSelectionCommand(sublime_plugin.TextCommand, sublime.View):
    def run(self, edit):
        word = selection_words(self.view)[0]
        CljSearchCommand(self.view.window()).on_done(word)
