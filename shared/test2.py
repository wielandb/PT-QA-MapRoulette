class NamedConstructor:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    @classmethod
    def create_person_from_dict(cls, person_data: dict):
        return cls(
            name = person_data['name'],
            age = person_data['age']
        )

test = NamedConstructor.create_person_from_dict({'name': 'Airton', 'age': 24})

print(test.name)
## output: Airton
