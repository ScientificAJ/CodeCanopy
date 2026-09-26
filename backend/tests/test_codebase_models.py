from app.models.codebase import Class, File, Function, Project, Relationship


def test_shared_models_serialize_as_one_codebase_contract() -> None:
    project = Project(
        id="project-1",
        name="Example",
        files=[
            File(
                path="src/auth.py",
                name="auth.py",
                language="python",
                size=128,
                functions=[
                    Function(
                        name="login",
                        file="src/auth.py",
                        line_start=10,
                        line_end=25,
                    )
                ],
                classes=[
                    Class(
                        name="Authenticator",
                        file="src/auth.py",
                        line_start=3,
                        line_end=30,
                    )
                ],
                imports=["database"],
            )
        ],
    )
    relationship = Relationship(source="src/auth.py", target="database", type="imports")

    serialized = project.model_dump()
    assert serialized["files"][0]["functions"][0]["file"] == "src/auth.py"
    assert serialized["files"][0]["classes"][0]["line_start"] == 3
    assert relationship.model_dump() == {
        "source": "src/auth.py",
        "target": "database",
        "type": "imports",
    }