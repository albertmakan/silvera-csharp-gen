# silvera-csharp-gen

This C# generator plug-in for [silvera](https://github.com/alensuljkanovic/silvera) is not yet on the Python Package Index (PyPi), but it can be installed from the GitHub repository with the following command:

```
$ pip install git+https://github.com/albertmakan/silvera-csharp-gen.git
```

This command will also install silvera if it is not already installed. Successful installation of silvera and the plug-in can be confirmed with the following command:

```
$ silvera list-generators
java-17 -> Java 17 code generator
csharp-10 -> C# 10 code generator
```

If the list includes java-17 and csharp-10, then silvera has successfully detected the plug-in.

A silvera project is a folder containing a silvera.project file and other .si files. Below is an example definition of a microservice. To result the microservice in a C# project, it is necessary to specify `lang="csharp"` in the deployment block.

```
import "user.si"

service SciPaper {
  deployment {
    lang="csharp"
  }

  api {
    @crud
    typedef Paper [
      @required str title
      str author
      str authorId
      @required list<Section> sections
    ]
    typedef Section [
      @required str name
      @required str content
    ]

    @rest(method=GET, mapping="by-author/{authorId}")
    list<Paper> getAllByAuthor(str authorId)

    @rest(method=POST)
    @producer(MsgGroup.PaperPublished -> Broker.PUBLISH_PAPER)
    void publish(str paperId, str authorId)
  }
}

dependency SciPaper -> User {
  getName[fail_silent]
}
```

The model is compiled with the following command:

```
$ silvera compile <project_dir> -o <output_dir>
```

If the model is successfully compiled, the generated code is located in the output_dir folder. To run the code, .NET 6 is required. In addition, a MongoDB instance needs to be running, and if the application uses messages, then Zookeeper and Kafka.

The program is started with the following command:

```
$ cd <output_dir>
$ dotnet run
```

CRUD methods will work, but calling additional functions will return status code 501 (Not Implemented). These functions need to be manually implemented.
