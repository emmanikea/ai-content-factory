@echo off
REM Start BOTH storefronts side by side:
REM   READY (before) on 8100 - every product's ad CONCEPTS are on the review board, nothing approved,
REM                            no videos. This is what you show, then approve a winner live.
REM   DONE  (after)  on 8101 - the approved winners, each with BOTH ads: the product PAN and the
REM                            ~24s UGC talking-head ad. The payoff.
cd /d "%~dp0"
python stage.py build >nul 2>&1
start "camber-ready" cmd /c "python dual_server.py ready 8100"
start "camber-done"  cmd /c "python dual_server.py done 8101"
timeout /t 2 >nul
start "" "http://localhost:8100"
start "" "http://localhost:8101"
echo.
echo  READY store (before): http://localhost:8100  (concepts to approve, nothing generated)
echo  DONE  store (after):  http://localhost:8101  (approved winners, pan + UGC per product)
