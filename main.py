from octosage.converters.doc_converter import DocConverter
import json


def main():
    try:
        file_path = "./sample/sample-cpu.pdf"
        converter = DocConverter()
        result = converter.convert(file_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        raise


if __name__ == "__main__":
    main()
