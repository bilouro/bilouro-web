from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hashtagjesus", "0002_hjblogpostpage_youtube_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="hjblogpostpage",
            name="chapter_title",
            field=models.CharField(blank=True, help_text="Book chapter title.", max_length=200),
        ),
        migrations.AddField(
            model_name="hjblogpostpage",
            name="biblical_ref",
            field=models.CharField(blank=True, help_text="Biblical reference (e.g. Mateus 7:1-5).", max_length=200),
        ),
        migrations.AddField(
            model_name="hjblogpostpage",
            name="biblical_text",
            field=models.TextField(blank=True, help_text="Biblical text with superscript verse numbers."),
        ),
        migrations.AddField(
            model_name="hjblogpostpage",
            name="chapter_reflection",
            field=models.TextField(blank=True, help_text="Pastoral reflection (2-4 paragraphs)."),
        ),
        migrations.AddField(
            model_name="hjblogpostpage",
            name="chapter_exercise",
            field=models.TextField(blank=True, help_text="Practical exercise."),
        ),
        migrations.AddField(
            model_name="hjblogpostpage",
            name="chapter_question",
            field=models.TextField(blank=True, help_text="Reflective question."),
        ),
    ]
