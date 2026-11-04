"""Bubblewrap-confined browser worker. JSON lines over stdin/stdout; no portal credential.

It renders a self-contained fictional form, reports element boxes so coordinate clicks can be
resolved to semantic targets, and performs only the four whitelisted commands. The model API
key never enters this process; the sandbox bind list excludes the workspace.
"""
import base64
import json
import os
import socket
import sys
from playwright.sync_api import sync_playwright


def emit(value):
    print(json.dumps(value, separators=(',', ':')), flush=True)


def main():
    init = json.loads(sys.stdin.readline())
    port = int(init.get('probe_port', 0))
    net_blocked = False
    if port:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.5):
                pass
        except OSError:
            net_blocked = True
    external_blocked = False
    try:
        with socket.create_connection(('1.1.1.1', 443), timeout=.5):
            pass
    except OSError:
        external_blocked = True
    system_readonly = False
    try:
        with open('/usr/proofpilot-isolation-test', 'w') as f:
            f.write('unexpected')
    except OSError:
        system_readonly = True
    boundary = {'host_port_unreachable': net_blocked, 'external_unreachable': external_blocked, 'system_readonly': system_readonly,
                'workspace_inaccessible': not os.path.exists('/home/user/proofpilot'), 'model_key_absent': not os.environ.get('MODEL_API_KEY'),
                'network_namespace': os.readlink('/proc/self/ns/net')}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-background-networking', '--disable-sync', '--disable-extensions'])
        context = browser.new_context(viewport={'width': 1100, 'height': 700}, service_workers='block', java_script_enabled=False, accept_downloads=False)
        context.route('**/*', lambda route: route.abort())
        page = context.new_page()
        page.set_content(init['html'], wait_until='load', timeout=10000)
        shipping = page.locator('#shipping')
        save = page.locator('#save')

        def boxes():
            out = {}
            for name, locator in (('shipping', shipping), ('save', save)):
                try:
                    box = locator.bounding_box(timeout=3000)
                except Exception:
                    box = None
                if box and all(isinstance(box.get(k), (int, float)) for k in ('x', 'y', 'width', 'height')):
                    out[name] = {'x': box['x'], 'y': box['y'], 'width': box['width'], 'height': box['height']}
            return out

        def observe():
            return base64.b64encode(page.screenshot(timeout=10000)).decode()

        def state():
            return {'ok': True, 'screenshot': observe(), 'input_value': shipping.input_value(timeout=5000), 'elements': boxes()}

        emit({'ok': True, 'boundary': boundary, 'screenshot': observe(), 'input_value': shipping.input_value(timeout=5000), 'elements': boxes()})
        for line in sys.stdin:
            cmd = json.loads(line)
            name = cmd.get('command')
            if name == 'close':
                emit({'ok': True})
                break
            if name == 'focus_shipping':
                shipping.focus(timeout=5000)
            elif name == 'fill_shipping':
                shipping.fill(cmd['value'], timeout=5000)
                emit({'ok': True, 'screenshot': observe(), 'input_value': shipping.input_value(timeout=5000), 'elements': boxes(), 'typing_mode': 'value_set'})
                continue
            elif name == 'type_shipping':
                # Prefer real key events, with select-all first when the entry replaces the field;
                # fall back to a direct value set and report which path was used.
                replace = bool(cmd.get('replace'))
                try:
                    if replace:
                        shipping.select_text(timeout=3000)
                    shipping.press_sequentially(cmd['text'], delay=0)
                    mode = 'keyboard'
                except Exception:
                    current = shipping.input_value(timeout=5000)
                    shipping.fill(cmd['text'] if replace else current + cmd['text'], timeout=5000)
                    mode = 'value_set'
                emit({'ok': True, 'screenshot': observe(), 'input_value': shipping.input_value(timeout=5000), 'elements': boxes(), 'typing_mode': mode})
                continue
            elif name == 'submit_shipping':
                save.click(timeout=5000)
            else:
                emit({'ok': False, 'error': 'unknown command'})
                continue
            emit(state())
        context.close()
        browser.close()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        emit({'ok': False, 'error_type': 'worker_failure', 'error': 'Sandbox worker stopped.'})
        sys.exit(1)
