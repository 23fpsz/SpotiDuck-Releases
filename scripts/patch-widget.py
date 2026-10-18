from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path('decoded')
ANDROID = '{http://schemas.android.com/apk/res/android}'


def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')


# 1) Report the active playlist/album title and five library shortcut names from the
# existing WebView library cache. This never triggers extra library network requests.
bridge_path = ROOT / 'assets/spotify_bridge.js'
bridge = bridge_path.read_text(encoding='utf-8')
old_state = '''        const currState = [
            window.track || "",
            window.artist || "",
            window.playing,
            window.repmode || "",
            window.shmode || "",
            window.isfav,
            window.cover || ""
        ].join('|');'''
new_state = '''        const playlistName = (() => {
            try {
                const path = window.location.pathname || "";
                if (path.includes('/collection/tracks')) return 'Liked Songs';
                if (/\\/(playlist|album)\\//.test(path)) {
                    const heading = document.querySelector('main h1') ||
                        document.querySelector('[data-testid="entityTitle"]') ||
                        document.querySelector('main [data-encore-id="text"] h1');
                    return heading ? (heading.innerText || heading.textContent || '').trim() : '';
                }
            } catch (_) {}
            return '';
        })();
        const mediaLib = window.mediaLib || {};
        const playlistItems = (mediaLib.playlists || []).filter(item => item && item.name && item.id);
        const albumItems = (mediaLib.albums || []).filter(item => item && item.name && item.id);
        const tileItems = [
            ...playlistItems.slice(0, 3).map(item => ({ item, kind: 'playlist' })),
            ...albumItems.slice(0, 2).map(item => ({ item, kind: 'album' }))
        ];
        const defaultTileNames = ['Liked Songs', 'Playlists', 'Made for you', 'Recently played', 'Albums'];
        const defaultTileUrls = [
            'spotify:collection:tracks',
            'spotify:collection:playlists',
            'spotify:section:0JQ5DAqbMKFzHmL4tf1CUd',
            'spotify:collection:recently-played',
            'spotify:collection:albums'
        ];
        const tileNames = Array.from({length: 5}, (_, i) => tileItems[i]?.item?.name || defaultTileNames[i]);
        const tileImages = Array.from({length: 5}, (_, i) => {
            const item = tileItems[i]?.item;
            const candidate = item?.image || item?.imageUrl || item?.cover || item?.images?.[0]?.url || '';
            return typeof candidate === 'string' ? candidate : '';
        });
        const tileUrls = Array.from({length: 5}, (_, i) => {
            const entry = tileItems[i];
            if (!entry) return defaultTileUrls[i];
            const item = entry.item;
            const raw = item.uri || item.spotifyUri || item.url || item.href || '';
            if (typeof raw === 'string' && raw.startsWith('spotify:')) return raw;
            if (typeof raw === 'string') {
                const match = raw.match(/open\\.spotify\\.com\\/(playlist|album)\\/([A-Za-z0-9]+)/);
                if (match) return 'spotify:' + match[1] + ':' + match[2];
            }
            return item.id ? 'spotify:' + entry.kind + ':' + item.id : defaultTileUrls[i];
        });
        const currState = [
            window.track || "",
            window.artist || "",
            window.playing,
            window.repmode || "",
            window.shmode || "",
            window.isfav,
            window.cover || "",
            playlistName,
            tileNames.join('|'),
            tileImages.join('|'),
            tileUrls.join('|')
        ].join('|');'''
if bridge.count(old_state) != 1:
    raise SystemExit('JS media state block did not match exactly; refusing patch.')
bridge = bridge.replace(old_state, new_state, 1)
old_values = '''                cover: window.cover || "",
                duration: window.duration || 0,
                position: window.position || 0'''
new_values = '''                cover: window.cover || "",
                playlist: playlistName,
                tile1: tileNames[0],
                tile2: tileNames[1],
                tile3: tileNames[2],
                tile4: tileNames[3],
                tile5: tileNames[4],
                tileImage1: tileImages[0],
                tileImage2: tileImages[1],
                tileImage3: tileImages[2],
                tileImage4: tileImages[3],
                tileImage5: tileImages[4],
                tileUrl1: tileUrls[0],
                tileUrl2: tileUrls[1],
                tileUrl3: tileUrls[2],
                tileUrl4: tileUrls[3],
                tileUrl5: tileUrls[4],
                duration: window.duration || 0,
                position: window.position || 0'''
if bridge.count(old_values) != 1:
    raise SystemExit('JS media metadata block did not match exactly; refusing patch.')
bridge = bridge.replace(old_values, new_values, 1)
bridge_path.write_text(bridge, encoding='utf-8')

# 1b) Prefer the browser's asynchronous Fetch API for player command traffic.
# The old path synchronously called nativeFetch() before trying normal fetch;
# nativeFetch has 10-second network timeouts and can block the WebView JS thread.
proxy_start = "        const strUrl = typeof url === 'string' ? url : (url && url.url ? url.url : '');"
proxy_end_marker = "\n    };\n\n    // =========================================================================\n    // SECTION 3: WAKE LOCK & BACKGROUND CONTROL"
if bridge.count(proxy_start) != 1:
    raise SystemExit('Could not uniquely find the synchronous fetch proxy block.')
proxy_start_at = bridge.index(proxy_start)
proxy_end_at = bridge.find(proxy_end_marker, proxy_start_at)
if proxy_end_at < 0:
    raise SystemExit('Could not find the end of the fetch wrapper; refusing unsafe patch.')
new_proxy = '''        const strUrl = typeof url === 'string' ? url : (url && url.url ? url.url : '');
        const needsNativeFallback = strUrl &&
            (strUrl.includes('connect-state') || strUrl.includes('melody/v1/msg'));

        // Let ordinary Fetch complete asynchronously first. This keeps long-poll or
        // player-command network traffic from blocking the WebView JavaScript thread.
        if (needsNativeFallback) {
            try {
                const response = await oriFetch(url, opts);
                if (response.status === 404 &&
                    strUrl.includes('connect-state') &&
                    strUrl.includes('/command/from/')) {
                    AndBridge.deferMessage('reload');
                    location.reload();
                }
                return response;
            } catch (fetchError) {
                // Keep the native path as a compatibility fallback for WebView/CORS
                // failures only; do not use it on every successful player request.
                try {
                    const reqHeaders = opts?.headers || {};
                    const reqBody = opts?.body
                        ? (typeof opts.body === 'string' ? opts.body : JSON.stringify(opts.body))
                        : null;
                    const rawRes = AndBridge.nativeFetch(
                        strUrl, method, JSON.stringify(reqHeaders), reqBody
                    );
                    if (rawRes) {
                        const parsed = JSON.parse(rawRes);
                        const status = parsed.status || 200;
                        const resBody = parsed.body || '';
                        return {
                            ok: status >= 200 && status < 300,
                            status: status,
                            statusText: status === 200 ? 'OK' : '',
                            headers: new Headers(parsed.headers || {}),
                            url: strUrl,
                            json: async () => JSON.parse(resBody || '{}'),
                            text: async () => resBody,
                            arrayBuffer: async () => new TextEncoder().encode(resBody).buffer,
                            clone: function() { return this; }
                        };
                    }
                } catch (nativeError) {
                    console.error('[Spotifuck] Native fetch fallback error:', nativeError);
                }
                throw fetchError;
            }
        }

        try {
            const resp = await oriFetch(url, opts);
            if (resp.status === 404 &&
                strUrl.includes('connect-state') &&
                strUrl.includes('/command/from/')) {
                AndBridge.deferMessage('reload');
                location.reload();
            }
            return resp;
        } catch (err) {
            throw err;
        }'''
bridge = bridge[:proxy_start_at] + new_proxy + bridge[proxy_end_at:]
bridge_path.write_text(bridge, encoding='utf-8')

# 2) Extend the existing native widget layouts without adding a new widget provider. without creating a separate widget/provider.
layout_path = ROOT / 'res/layout/widget_expanded.xml'
ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
tree = ET.parse(layout_path)
root = tree.getroot()
all_nodes = list(root.iter())
by_id = {n.get(ANDROID + 'id'): n for n in all_nodes if n.get(ANDROID + 'id')}
for required in ('@id/widget_root', '@id/top_section', '@id/info_container', '@id/controls_row', '@id/progress_row', '@id/btn_fav', '@id/btn_repeat'):
    if required not in by_id:
        raise SystemExit('Required native widget view missing: ' + required)
widget_root = by_id['@id/widget_root']
top = by_id['@id/top_section']
info = by_id['@id/info_container']
info.set(ANDROID + 'layout_width', 'match_parent')
info.attrib.pop(ANDROID + 'layout_toStartOf', None)
controls = by_id['@id/controls_row']
progress = by_id['@id/progress_row']

widget_root.set(ANDROID + 'layout_height', '252dp')
for control_id in ('@id/btn_shuffle', '@id/btn_prev', '@id/btn_play', '@id/btn_next', '@id/btn_repeat', '@id/btn_fav'):
    if control_id not in by_id:
        raise SystemExit('Required control is missing: ' + control_id)
for control_id in ('@id/btn_prev', '@id/btn_next'):
    by_id[control_id].set(ANDROID + 'layout_marginStart', '8dp')
    by_id[control_id].set(ANDROID + 'layout_marginEnd', '8dp')
play_frame = next((n for n in controls if n.tag.endswith('FrameLayout')), None)
if play_frame is None:
    raise SystemExit('Play control frame not found.')
play_frame.set(ANDROID + 'layout_width', '44dp')
play_frame.set(ANDROID + 'layout_height', '44dp')
play_frame.set(ANDROID + 'layout_marginStart', '8dp')
play_frame.set(ANDROID + 'layout_marginEnd', '8dp')
cover_frame = next((n for n in info if n.tag.endswith('FrameLayout')), None)
if cover_frame is not None:
    cover_frame.set(ANDROID + 'layout_width', '72dp')
    cover_frame.set(ANDROID + 'layout_height', '72dp')
title = by_id['@id/txt_title']
title.set(ANDROID + 'textSize', '14sp')
artist = by_id['@id/txt_artist']
artist.set(ANDROID + 'textSize', '12sp')
artist.set(ANDROID + 'text', '')
artist.set(ANDROID + 'visibility', 'gone')
title.set(ANDROID + 'singleLine', 'true')

# The updater calls RemoteViews.setTextViewText(txt_playlist) on both layout variants.
# Registering an ID alone is insufficient: Android rejects the update when that view
# is absent. Add a real subtitle in the expanded layout and a hidden placeholder in slim.
artist_parent = next((n for n in root.iter() if artist in list(n)), None)
if artist_parent is None:
    raise SystemExit('Could not find the title column for the playlist subtitle.')
if not any(n.get(ANDROID + 'id') == '@id/txt_playlist' for n in root.iter()):
    subtitle = ET.Element('TextView', {
        ANDROID + 'id': '@id/txt_playlist',
        ANDROID + 'layout_width': 'match_parent',
        ANDROID + 'layout_height': 'wrap_content',
        ANDROID + 'text': '',
        ANDROID + 'textSize': '10sp',
        ANDROID + 'textColor': '#ff9e9e9e',
        ANDROID + 'maxLines': '1',
        ANDROID + 'ellipsize': 'end'
    })
    artist_parent.insert(list(artist_parent).index(artist) + 1, subtitle)

compact_path = ROOT / 'res/layout/home_widget.xml'
compact_tree = ET.parse(compact_path)
compact_root = compact_tree.getroot()
compact_container = next((n for n in compact_root.iter()
                          if n.get(ANDROID + 'id') == '@id/content_container'), None)
if compact_container is None:
    raise SystemExit('Could not find compact widget content container.')
if not any(n.get(ANDROID + 'id') == '@id/txt_playlist' for n in compact_root.iter()):
    compact_subtitle = ET.Element('TextView', {
        ANDROID + 'id': '@id/txt_playlist',
        ANDROID + 'layout_width': 'match_parent',
        ANDROID + 'layout_height': 'wrap_content',
        ANDROID + 'text': '',
        ANDROID + 'textSize': '9sp',
        ANDROID + 'textColor': '#ff9e9e9e',
        ANDROID + 'maxLines': '1',
        ANDROID + 'ellipsize': 'end',
        ANDROID + 'visibility': 'gone'
    })
    full_title = next((n for n in compact_container.iter()
                       if n.get(ANDROID + 'id') == '@id/txt_fulltitle'), None)
    if full_title is None:
        raise SystemExit('Could not find compact widget title for subtitle insertion.')
    compact_container.insert(list(compact_container).index(full_title) + 1, compact_subtitle)
compact_tree.write(compact_path, encoding='utf-8', xml_declaration=True)

# Like belongs in the common six-control row rather than the artwork/title row.
fav_container = next((n for n in top if n.get(ANDROID + 'id') == '@id/fav_container'), None)
fav = by_id['@id/btn_fav']
if fav_container is not None:
    fav_container.remove(fav)
    top.remove(fav_container)
fav.set(ANDROID + 'layout_width', '28dp')
fav.set(ANDROID + 'layout_height', '28dp')
fav.set(ANDROID + 'contentDescription', 'Like')
fav.attrib.pop(ANDROID + 'tint', None)
# Existing native updater already assigns the favourite PendingIntent by ID.
if not any(n.get(ANDROID + 'id') == '@id/btn_fav' for n in list(controls)):
    controls.append(fav)

# Add a five-item row which uses the library names already cached by the player.
if not any(n.get(ANDROID + 'id') == '@id/playlist_tiles_row' for n in root.iter()):
    row = ET.Element('LinearLayout', {
        ANDROID + 'id': '@id/playlist_tiles_row',
        ANDROID + 'orientation': 'horizontal',
        ANDROID + 'gravity': 'center',
        ANDROID + 'layout_width': 'match_parent',
        ANDROID + 'layout_height': '52dp',
        ANDROID + 'layout_marginTop': '4dp'
    })
    defaults = ['Liked Songs', 'Made for you', 'Recently played', 'Playlists', 'Albums']
    for i, label in enumerate(defaults, 1):
        tile = ET.SubElement(row, 'LinearLayout', {
            ANDROID + 'id': f'@id/playlist_tile_{i}',
            ANDROID + 'orientation': 'vertical',
            ANDROID + 'layout_width': '0dp',
            ANDROID + 'layout_height': '52dp',
            ANDROID + 'layout_weight': '1',
            ANDROID + 'layout_marginHorizontal': '3dp',
            ANDROID + 'gravity': 'center',
            ANDROID + 'background': '@drawable/widget_slim_background',
            ANDROID + 'contentDescription': f'Library shortcut {i}'
        })
        ET.SubElement(tile, 'ImageView', {
            ANDROID + 'id': f'@id/playlist_tile_image_{i}',
            ANDROID + 'layout_width': 'match_parent',
            ANDROID + 'layout_height': '30dp',
            ANDROID + 'scaleType': 'centerCrop',
            ANDROID + 'src': '@drawable/widget_tile_placeholder'
        })
        ET.SubElement(tile, 'TextView', {
            ANDROID + 'id': f'@id/playlist_tile_label_{i}',
            ANDROID + 'layout_width': 'match_parent',
            ANDROID + 'layout_height': '18dp',
            ANDROID + 'gravity': 'center',
            ANDROID + 'text': label,
            ANDROID + 'textSize': '9sp',
            ANDROID + 'textColor': '#ffffffff',
            ANDROID + 'maxLines': '1',
            ANDROID + 'ellipsize': 'end'
        })
    children = list(widget_root)
    idx = children.index(progress)
    widget_root.insert(idx + 1, row)

tree.write(layout_path, encoding='utf-8', xml_declaration=True)

# Neutral placeholders avoid showing SpotiDuck branding before artwork loads.
placeholder_path = ROOT / 'res/drawable/widget_tile_placeholder.xml'
placeholder_path.write_text('''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="#FF292929" />
    <corners android:radius="8dp" />
</shape>
''', encoding='utf-8')
for target_layout in (layout_path, compact_path):
    target_root = ET.parse(target_layout).getroot()
    cover = next((n for n in target_root.iter() if n.get(ANDROID + 'id') == '@id/img_cover'), None)
    if cover is not None:
        cover.set(ANDROID + 'src', '@drawable/widget_tile_placeholder')
    if target_layout == layout_path:
        for node in target_root.iter():
            node_id = node.get(ANDROID + 'id') or ''
            if node_id.startswith('@id/playlist_tile_image_'):
                node.set(ANDROID + 'src', '@drawable/widget_tile_placeholder')
    ET.ElementTree(target_root).write(target_layout, encoding='utf-8', xml_declaration=True)

# 3) Register stable IDs for the five tiles and their parent row. IDs start after
# the highest ID in the inspected release's public resource table.
new_ids = {
    'playlist_tiles_row': '0x7f09022f',
    'playlist_tile_1': '0x7f090230',
    'playlist_tile_2': '0x7f090231',
    'playlist_tile_3': '0x7f090232',
    'playlist_tile_4': '0x7f090233',
    'playlist_tile_5': '0x7f090234',
    'playlist_tile_image_1': '0x7f090235',
    'playlist_tile_image_2': '0x7f090236',
    'playlist_tile_image_3': '0x7f090237',
    'playlist_tile_image_4': '0x7f090238',
    'playlist_tile_image_5': '0x7f090239',
    'playlist_tile_label_1': '0x7f09023a',
    'playlist_tile_label_2': '0x7f09023b',
    'playlist_tile_label_3': '0x7f09023c',
    'playlist_tile_label_4': '0x7f09023d',
    'playlist_tile_label_5': '0x7f09023e',
    'txt_playlist': '0x7f09023f',
}
public_path = ROOT / 'res/values/public.xml'
public = public_path.read_text(encoding='utf-8')
if 'name="widget_tile_placeholder"' not in public:
    public = public.replace('</resources>', '    <public type="drawable" name="widget_tile_placeholder" id="0x7f08013b" />\n</resources>', 1)
for name, value in new_ids.items():
    if f'name="{name}"' not in public:
        public = public.replace('</resources>', f'    <public type="id" name="{name}" id="{value}" />\n</resources>', 1)
public_path.write_text(public, encoding='utf-8')
ids_path = ROOT / 'res/values/ids.xml'
ids_text = ids_path.read_text(encoding='utf-8')
for name in new_ids:
    if f'name="{name}"' not in ids_text:
        ids_text = ids_text.replace('</resources>', f'    <item type="id" name="{name}" />\n</resources>', 1)
ids_path.write_text(ids_text, encoding='utf-8')

# 4) Add data slots to the native media state. The widget updater can now render
# a real playlist/album title when available, while preserving existing actions.
service_path = ROOT / 'smali/com/spotiduck/music/WebService.smali'
service = service_path.read_text(encoding='utf-8')
field_anchor = '.field public static r:Z = false'
fields = '''.field public static widgetPlaylist:Ljava/lang/String; = ""
.field public static widgetTile1:Ljava/lang/String; = "Liked Songs"
.field public static widgetTile2:Ljava/lang/String; = "Made for you"
.field public static widgetTile3:Ljava/lang/String; = "Recently played"
.field public static widgetTile4:Ljava/lang/String; = "Playlists"
.field public static widgetTile5:Ljava/lang/String; = "Albums"
.field public static widgetTileImage1:Ljava/lang/String; = ""
.field public static widgetTileImage2:Ljava/lang/String; = ""
.field public static widgetTileImage3:Ljava/lang/String; = ""
.field public static widgetTileImage4:Ljava/lang/String; = ""
.field public static widgetTileImage5:Ljava/lang/String; = ""
.field public static widgetTileUrl1:Ljava/lang/String; = "spotify:collection:tracks"
.field public static widgetTileUrl2:Ljava/lang/String; = "spotify:collection:playlists"
.field public static widgetTileUrl3:Ljava/lang/String; = "spotify:section:0JQ5DAqbMKFzHmL4tf1CUd"
.field public static widgetTileUrl4:Ljava/lang/String; = "spotify:collection:recently-played"
.field public static widgetTileUrl5:Ljava/lang/String; = "spotify:collection:albums"

'''
if service.count(field_anchor) != 1:
    raise SystemExit('Could not safely find WebService static-field insertion point.')
service = service.replace(field_anchor, fields + field_anchor, 1)
service_path.write_text(service, encoding='utf-8')

bridge_smali_path = ROOT / 'smali/com/spotiduck/music/AndBridge.smali'
smali = bridge_smali_path.read_text(encoding='utf-8')
anchor = '''    const-string p1, "cover"'''
insert = '''    const-string p1, "playlist"

    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p1

    sput-object p1, Lcom/spotiduck/music/WebService;->widgetPlaylist:Ljava/lang/String;

    const-string p1, "tile1"

    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p1

    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTile1:Ljava/lang/String;

    const-string p1, "tile2"

    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p1

    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTile2:Ljava/lang/String;

    const-string p1, "tile3"

    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p1

    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTile3:Ljava/lang/String;

    const-string p1, "tile4"

    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p1

    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTile4:Ljava/lang/String;

    const-string p1, "tile5"

    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p1

    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTile5:Ljava/lang/String;

    const-string p1, "tileImage1"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileImage1:Ljava/lang/String;

    const-string p1, "tileImage2"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileImage2:Ljava/lang/String;

    const-string p1, "tileImage3"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileImage3:Ljava/lang/String;

    const-string p1, "tileImage4"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileImage4:Ljava/lang/String;

    const-string p1, "tileImage5"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileImage5:Ljava/lang/String;

    const-string p1, "tileUrl1"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileUrl1:Ljava/lang/String;

    const-string p1, "tileUrl2"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileUrl2:Ljava/lang/String;

    const-string p1, "tileUrl3"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileUrl3:Ljava/lang/String;

    const-string p1, "tileUrl4"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileUrl4:Ljava/lang/String;

    const-string p1, "tileUrl5"
    invoke-virtual {p0, p1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;
    move-result-object p1
    sput-object p1, Lcom/spotiduck/music/WebService;->widgetTileUrl5:Ljava/lang/String;

    const-string p1, "cover"'''
if smali.count(anchor) != 1:
    raise SystemExit('Could not safely find AndBridge cover metadata insertion point.')
smali = smali.replace(anchor, insert, 1)
bridge_smali_path.write_text(smali, encoding='utf-8')

# Route library tile taps through MainActivity's existing spotify_uri handler.
receiver_path = ROOT / 'smali/com/spotiduck/music/WebService$MediaActionReceiver.smali'
receiver = receiver_path.read_text(encoding='utf-8')
receiver_anchor = '    const-string p0, "audio"'
if receiver.count(receiver_anchor) != 1:
    raise SystemExit('Could not locate MediaActionReceiver dispatch entry.')
tile_dispatch = '''    invoke-virtual {p2}, Landroid/content/Intent;->getAction()Ljava/lang/String;
    move-result-object v0
    invoke-static {p1, v0}, Lcom/spotiduck/music/WebService$MediaActionReceiver;->openWidgetTile(Landroid/content/Context;Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :widget_tile_not_handled
    return-void
    :widget_tile_not_handled

'''
receiver = receiver.replace(receiver_anchor, tile_dispatch + receiver_anchor, 1)
if '.method private static openWidgetTile(Landroid/content/Context;Ljava/lang/String;)Z' not in receiver:
    receiver_method = '''
.method private static openWidgetTile(Landroid/content/Context;Ljava/lang/String;)Z
    .locals 3

    if-eqz p1, :not_widget_tile
    const-string v0, "WIDGET_TILE_1"
    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-nez v0, :tile_one
    const-string v0, "WIDGET_TILE_2"
    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-nez v0, :tile_two
    const-string v0, "WIDGET_TILE_3"
    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-nez v0, :tile_three
    const-string v0, "WIDGET_TILE_4"
    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-nez v0, :tile_four
    const-string v0, "WIDGET_TILE_5"
    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :not_widget_tile
    sget-object v1, Lcom/spotiduck/music/WebService;->widgetTileUrl5:Ljava/lang/String;
    goto :launch_widget_tile

    :tile_one
    sget-object v1, Lcom/spotiduck/music/WebService;->widgetTileUrl1:Ljava/lang/String;
    goto :launch_widget_tile
    :tile_two
    sget-object v1, Lcom/spotiduck/music/WebService;->widgetTileUrl2:Ljava/lang/String;
    goto :launch_widget_tile
    :tile_three
    sget-object v1, Lcom/spotiduck/music/WebService;->widgetTileUrl3:Ljava/lang/String;
    goto :launch_widget_tile
    :tile_four
    sget-object v1, Lcom/spotiduck/music/WebService;->widgetTileUrl4:Ljava/lang/String;

    :launch_widget_tile
    if-eqz v1, :not_widget_tile
    invoke-virtual {v1}, Ljava/lang/String;->isEmpty()Z
    move-result v0
    if-nez v0, :not_widget_tile
    new-instance v2, Landroid/content/Intent;
    const-class v0, Lcom/spotiduck/music/MainActivity;
    invoke-direct {v2, p0, v0}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V
    const-string v0, "spotify_uri"
    invoke-virtual {v2, v0, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;
    const v0, 0x34000000
    invoke-virtual {v2, v0}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    invoke-virtual {p0, v2}, Landroid/content/Context;->startActivity(Landroid/content/Intent;)V
    const/4 v0, 0x1
    return v0

    :not_widget_tile
    const/4 v0, 0x0
    return v0
.end method
'''
    receiver = receiver.rstrip() + '\n' + receiver_method
receiver_path.write_text(receiver, encoding='utf-8')

# 5) The expanded widget's first line should read “Song Title • Artist”. The second
# line is populated with the active playlist/album title when detectable.
widget_builder_path = ROOT / 'smali/com/spotiduck/music/a.smali'
widget_builder = widget_builder_path.read_text(encoding='utf-8')
pattern_pair = re.compile(
    r"    sget-object v10, Lcom/spotiduck/music/WebService;->v:Ljava/lang/String;.*?"
    r"    invoke-virtual \{v7, v9, v10\}, Landroid/widget/RemoteViews;->setTextViewText\(ILjava/lang/CharSequence;\)V",
    re.DOTALL,
)
new_pair = '''    sget-object v10, Lcom/spotiduck/music/WebService;->v:Ljava/lang/String;

    const-string v6, " • "

    invoke-virtual {v10, v6}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v10

    sget-object v6, Lcom/spotiduck/music/WebService;->u:Ljava/lang/String;

    invoke-virtual {v10, v6}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v10

    invoke-virtual {v7, v11, v10}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V

    sget-object v10, Lcom/spotiduck/music/WebService;->widgetPlaylist:Ljava/lang/String;

    const v9, 0x7f09023f

    invoke-virtual {v7, v9, v10}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V'''
widget_builder, pair_count = pattern_pair.subn(lambda _: new_pair, widget_builder, count=1)
if pair_count != 1:
    raise SystemExit('Could not uniquely patch expanded title and subtitle assignment.')

# Set the five shortcut captions in expanded-mode RemoteViews.
click_pattern = re.compile(
    r"    invoke-virtual \{v7, v13, v0\}, Landroid/widget/RemoteViews;->setOnClickPendingIntent\(ILandroid/app/PendingIntent;\)V.*?    goto :goto_e",
    re.DOTALL,
)
click_insert = '''    invoke-virtual {v7, v13, v0}, Landroid/widget/RemoteViews;->setOnClickPendingIntent(ILandroid/app/PendingIntent;)V

    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile1:Ljava/lang/String;
    const v5, 0x7f09023a
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile2:Ljava/lang/String;
    const v5, 0x7f09023b
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile3:Ljava/lang/String;
    const v5, 0x7f09023c
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile4:Ljava/lang/String;
    const v5, 0x7f09023d
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile5:Ljava/lang/String;
    const v5, 0x7f09023e
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V

    const-string v4, "WIDGET_TILE_1"
    invoke-static {v0, v4}, Lcom/spotiduck/music/a;->a(Landroid/content/Context;Ljava/lang/String;)Landroid/app/PendingIntent;
    move-result-object v4
    const v5, 0x7f090230
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setOnClickPendingIntent(ILandroid/app/PendingIntent;)V
    const-string v4, "WIDGET_TILE_2"
    invoke-static {v0, v4}, Lcom/spotiduck/music/a;->a(Landroid/content/Context;Ljava/lang/String;)Landroid/app/PendingIntent;
    move-result-object v4
    const v5, 0x7f090231
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setOnClickPendingIntent(ILandroid/app/PendingIntent;)V
    const-string v4, "WIDGET_TILE_3"
    invoke-static {v0, v4}, Lcom/spotiduck/music/a;->a(Landroid/content/Context;Ljava/lang/String;)Landroid/app/PendingIntent;
    move-result-object v4
    const v5, 0x7f090232
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setOnClickPendingIntent(ILandroid/app/PendingIntent;)V
    const-string v4, "WIDGET_TILE_4"
    invoke-static {v0, v4}, Lcom/spotiduck/music/a;->a(Landroid/content/Context;Ljava/lang/String;)Landroid/app/PendingIntent;
    move-result-object v4
    const v5, 0x7f090233
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setOnClickPendingIntent(ILandroid/app/PendingIntent;)V
    const-string v4, "WIDGET_TILE_5"
    invoke-static {v0, v4}, Lcom/spotiduck/music/a;->a(Landroid/content/Context;Ljava/lang/String;)Landroid/app/PendingIntent;
    move-result-object v4
    const v5, 0x7f090234
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setOnClickPendingIntent(ILandroid/app/PendingIntent;)V

    goto :goto_e'''
widget_builder, click_count = click_pattern.subn(lambda _: click_insert, widget_builder, count=1)
if click_count != 1:
    raise SystemExit('Could not uniquely find native widget fav-action insertion point.')
# Replace the album-art fallback in this widget updater with a neutral placeholder.
method_start = widget_builder.find('.method public static d(Landroid/content/Context;Landroid/appwidget/AppWidgetManager;I)V')
method_end = widget_builder.find('.end method', method_start)
if method_start < 0 or method_end < 0:
    raise SystemExit('Could not isolate native widget update method for artwork patch.')
method_end += len('.end method')
widget_method = widget_builder[method_start:method_end]
widget_method = widget_method.replace('0x7f0800d6', '0x7f08013b')
image_call_anchor = ':goto_f\n    return-void\n.end method'
if widget_method.count(image_call_anchor) != 1:
    raise SystemExit('Could not find widget update return point for asynchronous tile artwork.')
widget_method = widget_method.replace(
    image_call_anchor,
    ':goto_f\n    if-eqz v3, :widget_tile_art_done\n'
    '    invoke-static {v0, v2, v7}, Lcom/spotiduck/music/a;->e(Landroid/content/Context;ILandroid/widget/RemoteViews;)V\n'
    '    :widget_tile_art_done\n    return-void\n.end method',
    1)
widget_builder = widget_builder[:method_start] + widget_method + widget_builder[method_end:]

loader_method = ['.method public static e(Landroid/content/Context;ILandroid/widget/RemoteViews;)V', '    .locals 7', '']
for i, image_id in enumerate(['0x7f090235', '0x7f090236', '0x7f090237', '0x7f090238', '0x7f090239'], 1):
    next_label = f':widget_tile_art_{i+1}' if i < 5 else ':widget_tile_art_done'
    loader_method.extend([
        f'    sget-object v1, Lcom/spotiduck/music/WebService;->widgetTileImage{i}:Ljava/lang/String;',
        f'    if-eqz v1, {next_label}',
        '    invoke-virtual {v1}, Ljava/lang/String;->isEmpty()Z',
        '    move-result v2',
        f'    if-nez v2, {next_label}',
        '    invoke-static {}, Lcom/squareup/picasso/Picasso;->get()Lcom/squareup/picasso/Picasso;',
        '    move-result-object v0',
        '    invoke-virtual {v0, v1}, Lcom/squareup/picasso/Picasso;->load(Ljava/lang/String;)Lcom/squareup/picasso/RequestCreator;',
        '    move-result-object v2',
        '    const/16 v3, 0x60',
        '    invoke-virtual {v2, v3, v3}, Lcom/squareup/picasso/RequestCreator;->resize(II)Lcom/squareup/picasso/RequestCreator;',
        '    move-result-object v2',
        '    invoke-virtual {v2}, Lcom/squareup/picasso/RequestCreator;->centerCrop()Lcom/squareup/picasso/RequestCreator;',
        '    move-result-object v2',
        '    const/4 v3, 0x1',
        '    new-array v4, v3, [I',
        '    const/4 v5, 0x0',
        '    aput p1, v4, v5',
        f'    const v3, {image_id}',
        '    invoke-virtual {v2, p2, v3, v4}, Lcom/squareup/picasso/RequestCreator;->into(Landroid/widget/RemoteViews;I[I)V',
        f'    {next_label}' if i < 5 else ''
    ])
loader_method.extend(['    return-void', '.end method', ''])
loader_text = '\n'.join(loader_method)
if 'widgetTileImage1' not in widget_builder:
    raise SystemExit('Widget image fields are not declared in the bridge state.')
widget_builder += loader_text
widget_builder_path.write_text(widget_builder, encoding='utf-8')

# Structural checks before rebuilding.
layout = ET.parse(layout_path).getroot()
layout_ids = [node.get(ANDROID + 'id') for node in layout.iter()]
required_tile_ids = ['playlist_tiles_row'] + [f'playlist_tile_{i}' for i in range(1, 6)]
required_tile_ids += [f'playlist_tile_image_{i}' for i in range(1, 6)]
required_tile_ids += [f'playlist_tile_label_{i}' for i in range(1, 6)]
for name in required_tile_ids:
    if layout_ids.count('@id/' + name) != 1:
        raise SystemExit('New widget ID missing or duplicated: ' + name)
for layout_file in (ROOT / 'res/layout/widget_expanded.xml', ROOT / 'res/layout/home_widget.xml'):
    layout_ids_here = [node.get(ANDROID + 'id') for node in ET.parse(layout_file).getroot().iter()]
    if layout_ids_here.count('@id/txt_playlist') != 1:
        raise SystemExit('Playlist subtitle must exist exactly once in ' + str(layout_file))
if bridge.index('const response = await oriFetch(url, opts);') > bridge.index('AndBridge.nativeFetch('):
    raise SystemExit('Native network proxy is still called before asynchronous fetch.')
for token in ['tile1:', 'tile2:', 'tile3:', 'tile4:', 'tile5:', 'tileImage1:', 'tileImage5:', 'tileUrl1:', 'tileUrl5:', 'playlist: playlistName']:
    if token not in bridge:
        raise SystemExit('JS media status is missing: ' + token)
if not placeholder_path.exists():
    raise SystemExit('Neutral widget artwork placeholder resource was not created.')
if 'private static openWidgetTile' not in receiver:
    raise SystemExit('Playlist shortcut receiver handler was not added.')
if 'Picasso;->load(Ljava/lang/String;)' not in widget_builder:
    raise SystemExit('Widget artwork loader was not added.')
for parent_id, label_id in [('0x7f090230', '0x7f09023a'), ('0x7f090231', '0x7f09023b'),
                            ('0x7f090232', '0x7f09023c'), ('0x7f090233', '0x7f09023d'),
                            ('0x7f090234', '0x7f09023e')]:
    if f'const v5, {label_id}\n    invoke-virtual {{v7, v5, v4}}, Landroid/widget/RemoteViews;->setTextViewText' not in widget_builder:
        raise SystemExit('Tile label must target its TextView: ' + label_id)
    if f'const v5, {parent_id}\n    invoke-virtual {{v7, v5, v4}}, Landroid/widget/RemoteViews;->setTextViewText' in widget_builder:
        raise SystemExit('Invalid setTextViewText target is a tile container: ' + parent_id)
print('Patched widget layout, artwork, tile routing, and controls with guarded checks.')
