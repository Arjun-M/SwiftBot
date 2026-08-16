import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Remove identifying fields from a real Telegram benchmark result.')
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding='utf-8'))
    identity = data.get('identity', {})
    chat = data.get('chat_check', {})
    safety = data.get('safety', {})

    data['identity'] = {
        'status': identity.get('status'),
        'is_bot': identity.get('is_bot'),
    }
    data['chat_check'] = {
        'status': chat.get('status'),
        'type': chat.get('type'),
        'expected_chat_id_matches': chat.get('expected_chat_id_matches'),
        'expected_username_matches': chat.get('expected_username_matches'),
    }
    data['safety'] = {
        'write_methods_called': safety.get('write_methods_called', []),
        'read_methods_called': safety.get('read_methods_called', []),
        'token_printed': safety.get('token_printed', False),
        'identifiers_removed': True,
    }
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote sanitized result to {args.output}')


if __name__ == '__main__':
    main()
