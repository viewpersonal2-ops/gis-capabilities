import json
import urllib.request
from lxml import etree

# Header penyamaran agar tidak diblokir Esri (403 Forbidden)
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print("Mengambil data waybackconfig.json terbaru...")
json_url = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"
req_json = urllib.request.Request(json_url, headers=headers)
with urllib.request.urlopen(req_json) as response:
    config_data = json.loads(response.read().decode('utf-8'))

print("Mengambil template WMTSCapabilities.xml resmi dari Esri...")
capabilities_url = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/WMTSCapabilities.xml"
req_cap = urllib.request.Request(capabilities_url, headers=headers)
with urllib.request.urlopen(req_cap) as response:
    xml_content = response.read()

# Parsing XML menggunakan lxml
parser = etree.XMLParser(remove_blank_text=True)
root = etree.fromstring(xml_content, parser)

# Pemetaan namespace resmi OGC
ns = {
    'wmts': 'http://www.opengis.net/wmts/1.0.0',
    'ows': 'http://www.opengis.net/ows/1.1'
}

contents = root.find('wmts:Contents', ns)
if contents is not None:
    # Hapus semua layer lama
    for layer in contents.findall('wmts:Layer', ns):
        contents.remove(layer)

    # Susun ulang layer berdasarkan config Esri
    for release_key, details in config_data.items():
        title = details.get('itemTitle', f'World Imagery (Wayback {release_key})')
        identifier = details.get('layerIdentifier', f'WB_{release_key}')
        
        # Mengambil itemURL resmi Esri jika ada, atau buat URL berbasis releaseNum
        item_url = details.get('itemURL', '')
        if item_url:
            # Konversi template variabel Esri ({level}/{row}/{col}) ke variabel resmi WMTS OGC
            template_url = item_url.replace('{level}', '{TileMatrix}').replace('{row}', '{TileRow}').replace('{col}', '{TileCol}')
            # Hilangkan /default028mm/ jika ada agar fleksibel di semua TileMatrixSet
            template_url = template_url.replace('/WMTS/1.0.0/default028mm/', '/WMTS/1.0.0/{TileMatrixSet}/')
        else:
            release_num = details.get('releaseNum', release_key)
            template_url = f'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/{{TileMatrixSet}}/MapServer/tile/{release_num}/{{TileMatrix}}/{{TileRow}}/{{TileCol}}'

        layer_el = etree.Element('{http://www.opengis.net/wmts/1.0.0}Layer')

        title_el = etree.Element('{http://www.opengis.net/ows/1.1}Title')
        title_el.text = title
        layer_el.append(title_el)

        id_el = etree.Element('{http://www.opengis.net/ows/1.1}Identifier')
        id_el.text = identifier
        layer_el.append(id_el)

        bbox_el = etree.Element('{http://www.opengis.net/ows/1.1}BoundingBox', crs='urn:ogc:def:crs:EPSG::3857')
        lc = etree.Element('{http://www.opengis.net/ows/1.1}LowerCorner')
        lc.text = '-20037508.34 -20037508.34'
        uc = etree.Element('{http://www.opengis.net/ows/1.1}UpperCorner')
        uc.text = '20037508.34 20037508.34'
        bbox_el.extend([lc, uc])
        layer_el.append(bbox_el)

        style_el = etree.Element('{http://www.opengis.net/wmts/1.0.0}Style', isDefault='true')
        st_title = etree.Element('{http://www.opengis.net/ows/1.1}Title')
        st_title.text = 'Default'
        st_id = etree.Element('{http://www.opengis.net/ows/1.1}Identifier')
        st_id.text = 'default'
        style_el.extend([st_title, st_id])
        layer_el.append(style_el)

        fmt_el = etree.Element('{http://www.opengis.net/wmts/1.0.0}Format')
        fmt_el.text = 'image/jpeg'
        layer_el.append(fmt_el)

        for tms_name in ['GoogleMapsCompatible', 'default028mm']:
            tms_link = etree.Element('{http://www.opengis.net/wmts/1.0.0}TileMatrixSetLink')
            tms_id = etree.Element('{http://www.opengis.net/wmts/1.0.0}TileMatrixSet')
            tms_id.text = tms_name
            tms_link.append(tms_id)
            layer_el.append(tms_link)

        res_url = etree.Element('{http://www.opengis.net/wmts/1.0.0}ResourceURL', {
            'format': 'image/jpeg',
            'resourceType': 'tile',
            'template': template_url
        })
        layer_el.append(res_url)
        contents.append(layer_el)

# Simpan XML
tree = etree.ElementTree(root)
tree.write('esri/WMTSCapabilities.xml', encoding='utf-8', xml_declaration=True, pretty_print=True)
print("File esri/WMTSCapabilities.xml berhasil diperbarui dengan URL tile presisi.")
