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
        const tileItems = [...(mediaLib.playlists || []), ...(mediaLib.albums || [])]
            .filter(item => item && item.name && item.id)
            .slice(0, 5);
        const defaultTileNames = ['Liked Songs', 'Made for you', 'Recently played', 'Playlists', 'Albums'];
        const tileNames = Array.from({length: 5}, (_, i) => tileItems[i]?.name || defaultTileNames[i]);
        const currState = [
            window.track || "",
            window.artist || "",
            window.playing,
            window.repmode || "",
            window.shmode || "",
            window.isfav,
            window.cover || "",
            playlistName,
            tileNames.join('|')
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
                duration: window.duration || 0,
                position: window.position || 0'''
if bridge.count(old_values) != 1:
    raise SystemExit('JS media metadata block did not match exactly; refusing patch.')
bridge = bridge.replace(old_values, new_values, 1)
bridge_path.write_text(bridge, encoding='utf-8')

# 2) Extend the existing widget layout without creating a separate widget/provider.
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

widget_root.set(ANDROID + 'layout_height', '244dp')
cover_frame = next((n for n in info if n.tag.endswith('FrameLayout')), None)
if cover_frame is not None:
    cover_frame.set(ANDROID + 'layout_width', '72dp')
    cover_frame.set(ANDROID + 'layout_height', '72dp')
title = by_id['@id/txt_title']
title.set(ANDROID + 'textSize', '14sp')
artist = by_id['@id/txt_artist']
artist.set(ANDROID + 'textSize', '12sp')
artist.set(ANDROID + 'text', '')

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
        ANDROID + 'layout_height': '48dp',
        ANDROID + 'layout_marginTop': '4dp'
    })
    defaults = ['Liked Songs', 'Made for you', 'Recently played', 'Playlists', 'Albums']
    for i, label in enumerate(defaults, 1):
        tile = ET.SubElement(row, 'LinearLayout', {
            ANDROID + 'id': f'@id/playlist_tile_{i}',
            ANDROID + 'orientation': 'vertical',
            ANDROID + 'layout_width': '0dp',
            ANDROID + 'layout_height': '48dp',
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
            ANDROID + 'src': '@drawable/widget_default_tile'
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
}
public_path = ROOT / 'res/values/public.xml'
public = public_path.read_text(encoding='utf-8')
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

    const-string p1, "cover"'''
if smali.count(anchor) != 1:
    raise SystemExit('Could not safely find AndBridge cover metadata insertion point.')
smali = smali.replace(anchor, insert, 1)
bridge_smali_path.write_text(smali, encoding='utf-8')

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
    const v5, 0x7f090230
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile2:Ljava/lang/String;
    const v5, 0x7f090231
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile3:Ljava/lang/String;
    const v5, 0x7f090232
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile4:Ljava/lang/String;
    const v5, 0x7f090233
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V
    sget-object v4, Lcom/spotiduck/music/WebService;->widgetTile5:Ljava/lang/String;
    const v5, 0x7f090234
    invoke-virtual {v7, v5, v4}, Landroid/widget/RemoteViews;->setTextViewText(ILjava/lang/CharSequence;)V

    goto :goto_e'''
widget_builder, click_count = click_pattern.subn(lambda _: click_insert, widget_builder, count=1)
if click_count != 1:
    raise SystemExit('Could not uniquely find native widget fav-action insertion point.')
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
for token in ['tile1:', 'tile2:', 'tile3:', 'tile4:', 'tile5:', 'playlist: playlistName']:
    if token not in bridge:
        raise SystemExit('JS media status is missing: ' + token)
print('Patched expanded widget metadata and five library shortcut captions with guarded checks.')
