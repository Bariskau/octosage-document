from octosage.converters.doc_converter import DocConverter
import json


def main():
    try:
        file_path = "./sample/test2.pdf"
        converter = DocConverter()
        result = converter.convert(file_path)
        print(json.dumps(result, indent=2))

    except Exception as e:
        raise


if __name__ == "__main__":
    main()
