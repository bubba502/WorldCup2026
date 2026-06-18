@echo off
cd /d C:\Users\tobri\AIAgency\clients\worldcup
python fetch_bbc_links.py >> bbc_links_log.txt 2>&1
