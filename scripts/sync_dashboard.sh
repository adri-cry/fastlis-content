#!/bin/bash
# Sync dashboard FastLIS: export data.json + stage media + kirim ke sabaraya-server.
# Dipanggil oleh cron konten & reels setelah tiap run. Idempoten.
set -u
BASE=/home/hatch/workspace/fastlis-content
DASH=/home/hatch/workspace/fastlis-dashboard
RENDERS=/home/hatch/workspace/fastlis-renders
TODAY=$(TZ=Asia/Jakarta date +%F)
SSH="ssh -p 2222 -i /home/hatch/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=20"
RSYNC="rsync -az --rsh=\"$SSH\""

echo "[sync] export data.json"
python3 "$BASE/scripts/export_dashboard.py" --out "$DASH/data.json" || { echo "[sync] export gagal"; exit 1; }

echo "[sync] stage media (semua tanggal yang ada di renders)"
for rd in "$RENDERS"/20*; do
  [ -d "$rd" ] || continue
  d=$(basename "$rd")
  mkdir -p "$DASH/media/$d"
  for i in 1 2 3 4 5; do
    [ -f "$rd/slide$i.png" ] && cp -f "$rd/slide$i.png" "$DASH/media/$d/"
  done
  # single: standarisasi nama single-post.png
  if [ -f "$rd/single-post.png" ]; then
    cp -f "$rd/single-post.png" "$DASH/media/$d/single-post.png"
  elif [ -f "$rd/single.png" ]; then
    cp -f "$rd/single.png" "$DASH/media/$d/single-post.png"
  fi
  [ -f "$rd/fastlis-reels.mp4" ] && cp -f "$rd/fastlis-reels.mp4" "$DASH/media/$d/"
done

# prune media staging lokal > 30 hari
find "$DASH/media" -maxdepth 1 -type d -name "20*" | while read -r d; do
  bn=$(basename "$d")
  if [ "$bn" \< "$(TZ=Asia/Jakarta date -d '30 days ago' +%F)" ]; then
    echo "[sync] prune lokal $bn"; rm -rf "$d"
  fi
done

echo "[sync] buka forwarder SSH"
~/workspace/bin/sabaraya-fwd.sh &>/dev/null &
sleep 4

echo "[sync] kirim ke server"
eval $RSYNC "$DASH/data.json" "$DASH/index.html" "$DASH/logo.png" "$DASH/DESIGN.md" root@localhost:/srv/fastlis-dashboard/ || echo "[sync] WARN: kirim data.json/index.html gagal"
eval $RSYNC --delete "$DASH/media/" root@localhost:/srv/fastlis-dashboard/media/ || echo "[sync] WARN: kirim media gagal"
# nginx (www-data) harus bisa baca: rsync membawa permission 660 lokal
$SSH root@localhost "chmod -R 755 /srv/fastlis-dashboard" 2>/dev/null || true
# prune media server > 30 hari
$SSH root@localhost "find /srv/fastlis-dashboard/media -maxdepth 1 -type d -name '20*' | while read -r d; do bn=\$(basename \"\$d\"); if [ \"\$bn\" \\< \"\$(date -d '30 days ago' +%F)\" ]; then echo \"prune server \$bn\"; rm -rf \"\$d\"; fi; done" 2>/dev/null || true

pkill -f "[s]abaraya-fwd.sh" 2>/dev/null; true
echo "[sync] selesai"
