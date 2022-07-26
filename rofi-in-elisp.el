;;; rofi-in-elisp.el --- An Elisp implementation of Rofi  -*- lexical-binding: t -*-

;; Copyright 2020 TRS-80
 
;; Author: TRS-80 <sourcehut.trs-80@isnotmyreal.name>
;; Version: 0.1
;; Package-Requires: (ivy)
;; Keywords: convenience, frames
;; URL: https://sr.ht/~trs-80/rofi-in-elisp

;; This file is not part of GNU Emacs.

;; This program is free software: you can redistribute it and/or
;; modify it under the terms of the GNU General Public License as
;; published by the Free Software Foundation, either version 3 of
;; the License, or (at your option) any later version.
;; 
;; This program is distributed in the hope that it will be
;; useful, but WITHOUT ANY WARRANTY; without even the implied
;; warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
;; PURPOSE.  See the GNU General Public License for more details.
;; 
;; You should have received a copy of the GNU General Public
;; License along with this program.  If not, see
;; <https://www.gnu.org/licenses/>.

;;; Commentary:

;; Coming from perspective of an Emacs user, I started running
;; into what I felt were limitations in Rofi[0].  So I decided to
;; re-implement Rofi in Emacs, and here is the result.
;; 
;; In fairness, this implementation is not nearly as feature
;; complete as Rofi (yet).  More like just a start.
;; 
;; See README for more information.
;; 
;; [0] https://github.com/davatorium/rofi

;;; Code:

;;* Variables

(defvar rofi-in-elisp-web-history-file
  "~/.config/rofi-in-elisp/history"
  "File to write history for web searches.")


(defvar rofi-in-elisp-web-provider-default "metager"
  "Default search provider for `rofi-in-elisp' (web modi).")


(defvar rofi-in-elisp-web-url-alist
  '(("aliexpress" . "https://www.aliexpress.com/wholesale?SearchText=")
    ("arch-wiki" . "https://wiki.archlinux.org/index.php?title=Special%3ASearch&fulltext=Search&search=")
    ("duckduckgo" . "https://www.duckduckgo.com/?q=")
    ("debian-packages" . "https://packages.debian.org/search?keywords=")
    ("emacswiki" . "https://www.emacswiki.org/emacs/Search?match=")
    ("f-droid" . "https://search.f-droid.org/?lang=en&q=")
    ("firefox-addons" . "https://addons.mozilla.org/en-US/firefox/search/?q=")
    ("github" . "https://github.com/search?q=")
    ("goodreads" . "https://www.goodreads.com/search?q=")
    ("hfqpdb" . "https://www.hfqpdb.com/search/")
    ("imdb" . "http://www.imdb.com/find?ref_=nv_sr_fn&q=")
    ("liberapay" . "https://liberapay.com/search?q=")
    ("melpa" . "https://melpa.org/#/?q=")
    ("metager" . "https://metager.org/meta/meta.ger3?eingabe=")
    ("ml-orgmode" . "https://orgmode.org/list/?q=")
    ("openhub" . "https://www.openhub.net/p?ref=homepage&query=")
    ("peertube" . "https://search.joinpeertube.org/search?search=")
    ("piratebay" . "https://thepiratebay.org/search/")
    ("proxy-opennic" . "http://proxy.opennicproject.org/proxy.php?hl=3e5&q=")
    ("reddit_subreddit" . "https://old.reddit.com/subreddits/search?q=")
    ("rfc_number" . "https://www.rfc-editor.org/search/rfc_search_detail.php?rfc=")
    ("rfc_title" . "https://www.rfc-editor.org/search/rfc_search_detail.php?title=")
    ("rottentomatoes" . "https://www.rottentomatoes.com/search/?search=")
    ("searchcode" . "https://searchcode.com/?q=")
    ("stackoverflow" . "http://stackoverflow.com/search?q=")
    ("startpage" . "https://www.startpage.com/do/dsearch?query=")
    ("swisscows" . "https://swisscows.com/web?query=")
    ("superuser" . "http://superuser.com/search?q=")
    ("symbolhound" . "http://symbolhound.com/?q=")
    ("url" . "")
    ("wikipedia" . "https://en.wikipedia.org/wiki/Special:Search?search=")
    ("yandex-com" . "https://yandex.com/search/?text=")
    ("yandex-com-images" . "https://yandex.com/images/search?text=")
    ("yandex-ru" . "https://yandex.ru/yandsearch?text=")
    ("youtube" . "https://www.youtube.com/results?search_query="))
  "Alist mapping providers to search URLs, to be used by
`rofi-in-elisp' function's 'web' search modi.")

;;* Functions
;; (require 'emacs-everywhere)

;;;###autoload
(defun rofi-in-elisp (modi)
  "Main function, but you should not be calling this from Emacs.

See README for setup instructions."
  (cond
    ;; Note: The "notify" modi was mostly for testing / playing
    ;; around.  If you want to use it, you will need to (require
    ;; 'notify) somewhere, as the function `notify' (below)
    ;; depends on it.
    ((string= modi "notify")
     (let* ((prompt (concat "Enter a message (" modi "): "))
            (my-msg (concat "You entered: "
                            (completing-read prompt
                                             '("a" "b" "c")))))
       (notify "rofi-in-elisp" my-msg)))
    ((string= modi "clipboard")
     (let* ((ivy-height (- (frame-parameter nil 'height) 1))
            ;; (app-info (emacs-everywhere-app-info))
            (selected-string (ivy-read "Choose string: "
                                       (split-string (shell-command-to-string "CM_LAUNCHER=rofi-script clipmenu") "\n" t))))
       (call-process "emacs_clip" nil 0 nil selected-string)
       (sleep-for 0.1)
       (call-process "xdotool" nil 0 nil "key" "--clearmodifiers" "Shift+Insert")))
    ((string= modi "web")
     (let* ((ivy-height (- (frame-parameter nil 'height) 1))
            (provider (ivy-read
                       "Choose provider: "
                       rofi-in-elisp-web-url-alist
                       :preselect rofi-in-elisp-web-provider-default))
            (provider_url (cdr
                           (assoc provider rofi-in-elisp-web-url-alist)))
            (history (mapcar (lambda (row)
                               (nth 2 row))
                             (reverse (ostrta-file-data-to-list
                                       rofi-in-elisp-web-history-file))))
            ;; We want to push the X CLIPBOARD and PRIMARY
            ;; selections both onto the top of the list for
            ;; convenience.
            (history-and-clipboard
              (progn (let ((clipboard (gui-get-selection 'CLIPBOARD))
                           (primary (gui-get-selection 'PRIMARY))
                           (h-a-c history))
                       (unless (null clipboard)
                         (push clipboard h-a-c))
                       (unless (null primary)
                         (push primary h-a-c))
                       h-a-c)))
            (query (ivy-read
                    "Query: "
                    history-and-clipboard))
            (query-url (concat provider_url query))
            (timestamp (format-time-string "%F %T"))
            (history-line (concat timestamp "" provider "" query "\n")))
       (call-process "xdg-open" nil 0 nil query-url)
       (with-current-buffer (find-file-noselect
                             rofi-in-elisp-web-history-file)
         (goto-char (point-max))
         (insert history-line)
         (save-buffer)))))
  ;; 2020-10-30 NOTE: I already tried to put an other-window
  ;; command after delete-frame, below, but that didn't work,
  ;; either.  lol.  Still getting this annoying behavior where I
  ;; end up in minibuffer (of some other Emacs window) after
  ;; exiting.
  (delete-frame))




;;* Provide / End

(provide 'rofi-in-elisp)

;;; rofi-in-elisp.el ends here
