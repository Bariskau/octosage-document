from octosage.converters.doc_converter import DocConverter
import json
from octosage.operations.sort_operation import SortOperation


def main():
    try:
        file_path = "./sample/sample-cpu.pdf"
        converter = DocConverter()
        result = converter.convert(file_path)
        sort_operator = SortOperation()
        result = sort_operator.sort(result)

        with open("output.json", "w") as file:
            json.dump(result, file, indent=2, ensure_ascii=False)

    except Exception as e:
        raise


if __name__ == "__main__":
    main()
