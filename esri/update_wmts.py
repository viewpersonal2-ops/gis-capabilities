import json
import urllib.request
import xml.etree.ElementTree as ET

# Header penyamaran agar tidak ditolak oleh server Esri (403 Forbidden)
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

ET.register_namespace('', 'http://www.opengis.net/wmts/1.0.0')
ET.register_namespace('ows', 'http://www.opengis.net/ows/1.1')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

root = ET.fromstring(xml_content)
ns = {
    'wmts': 'http://www.opengis.net/wmts/1.0.0',
    'ows': 'http://www.opengis.net/ows/1.1'
}

contents = root.find('wmts:Contents', ns)
if contents is not None:
    for layer in contents.findall('wmts:Layer', ns):
        contents.remove(layer)

    for release_id, details in config_data.items():
        title = details.get('itemTitle', f'World Imagery (Wayback {release_id})')
        identifier = details.get('layerIdentifier', f'WB_{release_id}')

        layer_el = ET.Element('{http://www.opengis.net/wmts/1.0.0}Layer')
        
        title_el = ET.Element('{http://www.opengis.net/ows/1.1}Title')
        title_el.text = title
        layer_el.append(title_el)

        id_el = ET.Element('{http://www.opengis.net/ows/1.1}Identifier')
        id_el.text = identifier
        layer_el.append(id_el)

        bbox_el = ET.Element('{http://www.opengis.net/ows/1.1}BoundingBox', {'crs': 'urn:ogc:def:crs:EPSG::3857'})
        lc = ET.Element('{http://www.opengis.net/ows/1.1}LowerCorner')
        lc.text = '-20037508.34 -20037508.34'
        uc = ET.Element('{http://www.opengis.net/ows/1.1}UpperCorner')
        uc.text = '20037508.34 20037508.34'
        bbox_el.extend([lc, uc])
        layer_el.append(bbox_el)

        style_el = ET.Element('{http://www.opengis.net/wmts/1.0.0}Style', {'isDefault': 'true'})
        st_title = ET.Element('{http://www.opengis.net/ows/1.1}Title')
        st_title.text = 'Default'
        st_id = ET.Element('{http://www.opengis.net/ows/1.1}Identifier')
        st_id.text = 'default'
        style_el.extend([st_title, st_id])
        layer_el.append(style_el)

        fmt_el = ET.Element('{http://www.opengis.net/wmts/1.0.0}Format')
        fmt_el.text = 'image/jpeg'
        layer_el.append(fmt_el)

        for tms_name in ['GoogleMapsCompatible', 'default028mm']:
            tms_link = ET.Element('{http://www.opengis.net/wmts/1.0.0}TileMatrixSetLink')
            tms_id = ET.Element('{http://www.opengis.net/wmts/1.0.0}TileMatrixSet')
            tms_id.text = tms_name
            tms_link.append(tms_id)
            layer_el.append(tms_link)

        res_url = ET.Element('{http://www.opengis.net/wmts/1.0.0}ResourceURL', {
            'format': 'image/jpeg',
            'resourceType': 'tile',
            'template': f'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/{{TileMatrixSet}}/MapServer/tile/{release_id}/{{TileMatrix}}/{{TileRow}}/{{TileCol}}'
        })
        layer_el.append(res_url)
        contents.append(layer_el)

tree = ET.ElementTree(root)
tree.write('esri/WMTSCapabilities.xml', encoding='utf-8', xml_declaration=True)
print("File esri/WMTSCapabilities.xml berhasil diperbarui.")
